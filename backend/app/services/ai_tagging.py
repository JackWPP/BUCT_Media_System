"""
AI 打标服务模块
使用 Ollama 本地视觉语言模型进行图片内容分析
"""
import json
import base64
import httpx
import logging
from typing import Dict, Any, Optional
from PIL import Image
import io

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AITaggingService:
    """AI 打标服务类"""
    
    def __init__(self):
        self.ollama_url = settings.OLLAMA_API_URL
        self.model_name = settings.AI_MODEL_NAME
        self.enabled = settings.AI_ENABLED
        
    async def analyze_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """
        分析图片内容,返回标签信息
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            包含 season, category, objects 的字典,或 None (失败时)
        """
        if not self.enabled:
            logger.info("AI 服务已禁用,跳过分析")
            return None
            
        try:
            # 压缩图片并转为 base64
            image_base64 = self._compress_and_encode_image(image_path)
            
            # 构建 Prompt
            prompt = self._build_prompt()
            
            # 调用 Ollama API
            result = await self._call_ollama_api(image_base64, prompt)
            
            # 解析结果
            parsed_result = self._parse_response(result)
            
            logger.info(f"AI 分析成功: {parsed_result}")
            return parsed_result
            
        except Exception as e:
            logger.error(f"AI 分析失败: {str(e)}")
            return None
    
    def _compress_and_encode_image(self, image_path: str, max_size: int = 1024) -> str:
        """
        压缩图片并转为 base64 编码
        
        Args:
            image_path: 图片路径
            max_size: 最大边长 (像素)
            
        Returns:
            base64 编码的图片字符串
        """
        with Image.open(image_path) as img:
            # 转换为 RGB (如果是 RGBA)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # 计算缩放比例
            width, height = img.size
            if max(width, height) > max_size:
                ratio = max_size / max(width, height)
                new_size = (int(width * ratio), int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # 转为 JPEG 并编码为 base64
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            image_bytes = buffer.getvalue()
            
            return base64.b64encode(image_bytes).decode('utf-8')
    
    def _build_prompt(self) -> str:
        """
        构建标准 Prompt
        
        Returns:
            Prompt 字符串
        """
        return """请分析这张图片。

1. 判断季节 (Spring/Summer/Autumn/Winter)。

2. 判断场景类型 (Landscape/Portrait/Activity/Documentary)。

3. 提取画面中的关键物体 (不超过5个) 使用中文标签。

请以纯JSON格式返回，不要包含Markdown格式标记，格式如下:

{
    "season": "...",
    "category": "...",
    "objects": ["...", "..."]
}"""
    
    async def _call_ollama_api(
        self, 
        image_base64: str, 
        prompt: str,
        timeout: int = 60
    ) -> str:
        """
        调用 Ollama API
        
        Args:
            image_base64: base64 编码的图片
            prompt: 提示词
            timeout: 超时时间(秒)
            
        Returns:
            API 返回的响应文本
        """
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get("response", "")
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析 AI 返回的 JSON 响应
        
        Args:
            response_text: API 返回的文本
            
        Returns:
            解析后的字典
        """
        # 移除可能的 Markdown 代码块标记
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # 解析 JSON
        try:
            result = json.loads(text)
            
            # 验证必需字段
            if "season" not in result or "category" not in result or "objects" not in result:
                raise ValueError("响应缺少必需字段")
            
            # 验证 season 值
            valid_seasons = ["Spring", "Summer", "Autumn", "Winter"]
            if result["season"] not in valid_seasons:
                logger.warning(f"无效的 season 值: {result['season']}, 使用默认值 Spring")
                result["season"] = "Spring"
            
            # 验证 category 值
            valid_categories = ["Landscape", "Portrait", "Activity", "Documentary"]
            if result["category"] not in valid_categories:
                logger.warning(f"无效的 category 值: {result['category']}, 使用默认值 Landscape")
                result["category"] = "Landscape"
            
            # 确保 objects 是列表
            if not isinstance(result["objects"], list):
                result["objects"] = []
            
            # 限制最多 5 个标签
            result["objects"] = result["objects"][:5]
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {str(e)}, 原始文本: {text}")
            # 返回默认值
            return {
                "season": "Spring",
                "category": "Landscape",
                "objects": []
            }


# 创建全局服务实例
ai_service = AITaggingService()


async def analyze_photo_with_ai(image_path: str) -> Optional[Dict[str, Any]]:
    """
    使用 AI 分析照片 (便捷函数)
    
    Args:
        image_path: 图片路径
        
    Returns:
        分析结果或 None
    """
    return await ai_service.analyze_image(image_path)
