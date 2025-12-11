"""
批量导入 API 端点
"""
import os
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from app.core.deps import get_db, get_current_admin_user
from app.models.user import User
from app.services.import_service import scan_and_parse_json_files, import_service, sanitize_exif_data
from app.services.storage import ensure_upload_dirs
from app.services.image_processing import process_uploaded_image
from app.crud import photo as photo_crud
from app.crud import tag as tag_crud

logger = logging.getLogger(__name__)

router = APIRouter()


class ImportRequest(BaseModel):
    """导入请求"""
    json_path: str
    image_folder: Optional[str] = None


class ImportResponse(BaseModel):
    """导入响应"""
    total_count: int
    imported_count: int
    skipped_count: int
    error_count: int
    errors: list[str]
    message: str


@router.post("/import", response_model=ImportResponse)
async def import_photos(
    request: ImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    批量导入照片数据
    
    - **json_path**: JSON 文件或目录路径
    - **image_folder**: 可选的图片文件夹路径
    
    仅管理员可用
    """
    logger.info(f"开始批量导入: json_path={request.json_path}, image_folder={request.image_folder}")
    
    # 验证路径存在
    if not os.path.exists(request.json_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"路径不存在: {request.json_path}"
        )
    
    # 扫描并解析 JSON 文件
    photos_data, parse_errors = scan_and_parse_json_files(
        request.json_path,
        request.image_folder
    )
    
    if not photos_data:
        return ImportResponse(
            total_count=0,
            imported_count=0,
            skipped_count=0,
            error_count=len(parse_errors),
            errors=parse_errors,
            message="未找到有效的照片数据"
        )
    
    # 统计信息
    total_count = len(photos_data)
    imported_count = 0
    skipped_count = 0
    error_count = 0
    errors = list(parse_errors)  # 复制解析错误
    
    # 确保上传目录存在
    originals_dir, thumbnails_dir = ensure_upload_dirs()
    
    # 处理每条照片数据
    for photo_data in photos_data:
        try:
            photo_uuid = photo_data.get('uuid')
            filename = photo_data.get('filename', 'unknown.jpg')
            
            # 检查是否已存在
            existing_photo = await photo_crud.get_photo(db, photo_uuid)
            if existing_photo:
                logger.info(f"照片已存在,跳过: {photo_uuid} - {filename}")
                skipped_count += 1
                continue
            
            # 查找图片文件
            json_dir = photo_data.get('_json_dir', os.path.dirname(request.json_path))
            image_path = import_service.find_image_file(
                photo_data,
                json_dir,
                request.image_folder
            )
            
            if not image_path:
                error_msg = f"未找到图片文件: {filename}"
                logger.warning(error_msg)
                errors.append(error_msg)
                error_count += 1
                continue
            
            # 复制图片到 uploads 目录
            file_extension = os.path.splitext(filename)[1] or '.jpg'
            original_filename = f"{photo_uuid}{file_extension}"
            original_dest = os.path.join(originals_dir, original_filename)
            
            shutil.copy2(image_path, original_dest)
            logger.info(f"复制图片: {image_path} -> {original_dest}")
            
            # 处理图片 (生成缩略图, 提取 EXIF)
            processing_result = process_uploaded_image(original_dest, photo_uuid)
            
            # 获取文件大小
            file_size = os.path.getsize(original_dest)
            
            # 提取标签信息
            season, category, keywords = import_service.extract_tags_from_data(photo_data)
            
            # 提取 EXIF 信息
            exif_data = import_service.extract_exif_from_data(photo_data)
            # 合并处理后的 EXIF
            exif_data.update(processing_result.get('exif_data', {}))
            # 清理EXIF数据，确保可JSON序列化
            exif_data = sanitize_exif_data(exif_data)
            
            # 创建照片记录
            new_photo_data = {
                'id': photo_uuid,
                'filename': filename,
                'original_path': photo_data.get('original_path', image_path),
                'thumb_path': processing_result.get('thumb_path'),
                'width': photo_data.get('width') or processing_result.get('width'),
                'height': photo_data.get('height') or processing_result.get('height'),
                'file_size': file_size,
                'mime_type': f'image/{file_extension[1:]}',
                'exif_data': exif_data,
                'captured_at': processing_result.get('captured_at'),
                'description': photo_data.get('description'),
                'season': season,
                'category': category,
                'status': 'pending',  # 导入的照片默认待审核
                'processing_status': 'manual'  # 已经打过标,不需要 AI 处理
            }
            
            photo = await photo_crud.create_photo(db, new_photo_data, str(current_user.id))
            
            # 处理标签
            if keywords:
                tag_ids = []
                for keyword in keywords:
                    # 获取或创建标签
                    tag = await tag_crud.get_or_create_tag(db, keyword.lower())
                    tag_ids.append(tag.id)
                
                # 添加标签关联
                if tag_ids:
                    await photo_crud.add_tags_to_photo(db, photo_uuid, tag_ids)
            
            imported_count += 1
            logger.info(f"成功导入照片: {photo_uuid} - {filename}")
            
        except Exception as e:
            error_msg = f"导入失败: {photo_data.get('filename', 'unknown')} - {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            error_count += 1
            # 回滚事务，以便继续处理下一个
            await db.rollback()
    
    # 返回结果
    message = f"导入完成: 总计 {total_count} 张, 成功 {imported_count} 张, 跳过 {skipped_count} 张, 失败 {error_count} 张"
    
    return ImportResponse(
        total_count=total_count,
        imported_count=imported_count,
        skipped_count=skipped_count,
        error_count=error_count,
        errors=errors[:100],  # 限制错误信息数量
        message=message
    )


@router.get("/import/validate")
async def validate_import_path(
    json_path: str,
    current_user: User = Depends(get_current_admin_user)
):
    """
    验证导入路径
    
    检查路径是否存在以及包含多少 JSON 文件
    """
    if not os.path.exists(json_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"路径不存在: {json_path}"
        )
    
    # 扫描 JSON 文件
    json_files = import_service.scan_json_files(json_path)
    
    return {
        "path": json_path,
        "exists": True,
        "is_file": os.path.isfile(json_path),
        "is_directory": os.path.isdir(json_path),
        "json_files_count": len(json_files),
        "json_files": json_files[:10]  # 最多返回前 10 个
    }
