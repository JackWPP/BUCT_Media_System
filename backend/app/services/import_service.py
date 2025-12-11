"""
批量导入服务模块
用于从 BUCT Tagger 系统导入照片数据
"""
import json
import os
import shutil
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class ImportService:
    """导入服务类"""
    
    def __init__(self):
        pass
    
    def scan_json_files(self, directory: str) -> List[str]:
        """
        递归扫描目录中的所有 JSON 文件
        
        Args:
            directory: 目录路径
            
        Returns:
            JSON 文件路径列表
        """
        json_files = []
        
        if not os.path.exists(directory):
            logger.error(f"目录不存在: {directory}")
            return json_files
        
        # 如果是单个文件
        if os.path.isfile(directory) and directory.lower().endswith('.json'):
            return [directory]
        
        # 递归扫描目录
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.json'):
                    json_path = os.path.join(root, file)
                    json_files.append(json_path)
                    logger.info(f"找到 JSON 文件: {json_path}")
        
        logger.info(f"共找到 {len(json_files)} 个 JSON 文件")
        return json_files
    
    def parse_json_file(self, json_path: str) -> Optional[List[Dict[str, Any]]]:
        """
        解析单个 JSON 文件
        
        Args:
            json_path: JSON 文件路径
            
        Returns:
            照片数据列表,或 None (解析失败时)
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 支持两种格式:
            # 1. 数组格式: [{photo1}, {photo2}, ...]
            # 2. 对象格式: {"photos": [{...}]} 或单个对象 {...}
            
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                # 如果有 photos 字段
                if 'photos' in data:
                    return data['photos']
                # 否则作为单个照片对象
                else:
                    return [data]
            else:
                logger.error(f"不支持的 JSON 格式: {json_path}")
                return None
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {json_path}, 错误: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"读取文件失败: {json_path}, 错误: {str(e)}")
            return None
    
    def validate_photo_data(self, photo_data: Dict[str, Any]) -> bool:
        """
        验证照片数据格式
        
        Args:
            photo_data: 照片数据字典
            
        Returns:
            是否有效
        """
        # 必需字段
        required_fields = ['uuid', 'filename']
        
        for field in required_fields:
            if field not in photo_data:
                logger.warning(f"照片数据缺少必需字段: {field}")
                return False
        
        return True
    
    def find_image_file(
        self,
        photo_data: Dict[str, Any],
        json_dir: str,
        image_folder: Optional[str] = None
    ) -> Optional[str]:
        """
        智能查找图片文件
        
        Args:
            photo_data: 照片数据
            json_dir: JSON 文件所在目录
            image_folder: 可选的图片文件夹路径
            
        Returns:
            图片文件路径,或 None
        """
        filename = photo_data.get('filename', '')
        original_path = photo_data.get('original_path', '')
        
        # 尝试的路径列表
        search_paths = []
        
        # 1. 使用 original_path (如果是绝对路径且存在)
        if original_path and os.path.isabs(original_path):
            search_paths.append(original_path)
        
        # 2. JSON 同级目录
        if filename:
            search_paths.append(os.path.join(json_dir, filename))
        
        # 3. 指定的 image_folder
        if image_folder and filename:
            search_paths.append(os.path.join(image_folder, filename))
        
        # 4. JSON 目录下的 images/ 子目录
        if filename:
            search_paths.append(os.path.join(json_dir, 'images', filename))
        
        # 5. JSON 目录的父目录
        if filename:
            parent_dir = os.path.dirname(json_dir)
            search_paths.append(os.path.join(parent_dir, filename))
            search_paths.append(os.path.join(parent_dir, 'images', filename))
        
        # 6. 尝试相对路径 (original_path 作为相对路径)
        if original_path and not os.path.isabs(original_path):
            search_paths.append(os.path.join(json_dir, original_path))
            if image_folder:
                search_paths.append(os.path.join(image_folder, original_path))
        
        # 尝试查找文件
        for path in search_paths:
            if path and os.path.exists(path) and os.path.isfile(path):
                logger.info(f"找到图片文件: {path}")
                return path
        
        logger.warning(f"未找到图片文件: {filename}")
        logger.debug(f"尝试的路径: {search_paths}")
        return None
    
    def extract_tags_from_data(self, photo_data: Dict[str, Any]) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        从照片数据中提取标签信息
        
        Args:
            photo_data: 照片数据
            
        Returns:
            (season, category, keywords)
        """
        season = None
        category = None
        keywords = []
        
        # 检查 tags 字段
        tags = photo_data.get('tags', {})
        
        if isinstance(tags, dict):
            # 提取 attributes
            attributes = tags.get('attributes', {})
            if isinstance(attributes, dict):
                season = attributes.get('season')
                category = attributes.get('category')
            
            # 提取 keywords
            keywords_data = tags.get('keywords', [])
            if isinstance(keywords_data, list):
                keywords = [str(k) for k in keywords_data]
        
        return season, category, keywords
    
    def extract_exif_from_data(self, photo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        从照片数据中提取 EXIF 信息
        
        Args:
            photo_data: 照片数据
            
        Returns:
            EXIF 数据字典
        """
        tags = photo_data.get('tags', {})
        
        if isinstance(tags, dict):
            meta = tags.get('meta', {})
            if isinstance(meta, dict):
                return meta
        
        return {}


# 创建全局实例
import_service = ImportService()


def scan_and_parse_json_files(
    path: str,
    image_folder: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    扫描并解析 JSON 文件 (便捷函数)
    
    Args:
        path: JSON 文件或目录路径
        image_folder: 可选的图片文件夹路径
        
    Returns:
        (照片数据列表, 错误信息列表)
    """
    errors = []
    all_photos = []
    
    # 扫描 JSON 文件
    json_files = import_service.scan_json_files(path)
    
    if not json_files:
        errors.append(f"未找到 JSON 文件: {path}")
        return all_photos, errors
    
    # 解析每个 JSON 文件
    for json_file in json_files:
        photos = import_service.parse_json_file(json_file)
        
        if photos is None:
            errors.append(f"解析失败: {json_file}")
            continue
        
        # 验证并添加额外信息
        json_dir = os.path.dirname(json_file)
        
        for photo_data in photos:
            # 验证数据
            if not import_service.validate_photo_data(photo_data):
                errors.append(f"数据格式无效: {photo_data.get('filename', 'unknown')}")
                continue
            
            # 添加 JSON 路径信息
            photo_data['_json_path'] = json_file
            photo_data['_json_dir'] = json_dir
            
            all_photos.append(photo_data)
    
    logger.info(f"成功解析 {len(all_photos)} 条照片数据")
    
    return all_photos, errors
