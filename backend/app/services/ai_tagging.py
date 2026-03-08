"""
AI analysis services with provider abstraction and fallback.
"""
import base64
import io
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
from PIL import Image

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


DEFAULT_RESULT = {
    "summary": "",
    "classifications": {
        "season": None,
        "campus": None,
        "building": None,
        "gallery_series": None,
        "gallery_year": None,
        "photo_type": None,
    },
    "free_tags": [],
    "quality_flags": [],
    "risk_flags": [],
    "confidence": 0.0,
}


class BaseAIProvider(ABC):
    """Common AI provider contract."""

    provider_name: str

    @property
    @abstractmethod
    def model_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def analyze(self, image_base64: str, prompt: str) -> str:
        raise NotImplementedError


class OllamaProvider(BaseAIProvider):
    provider_name = "ollama"
    model_override: str | None = None

    @property
    def model_id(self) -> str:
        return self.model_override or settings.AI_MODEL_ID or settings.AI_MODEL_NAME

    async def analyze(self, image_base64: str, prompt: str) -> str:
        url = f"{settings.OLLAMA_API_URL}/api/generate"
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")


class DashScopeVLMProvider(BaseAIProvider):
    provider_name = "dashscope"
    model_override: str | None = None

    @property
    def model_id(self) -> str:
        return self.model_override or settings.AI_MODEL_ID or "qwen-vl-max"

    async def analyze(self, image_base64: str, prompt: str) -> str:
        if not settings.DASHSCOPE_API_KEY:
            raise RuntimeError("DASHSCOPE_API_KEY is not configured.")

        url = f"{settings.DASHSCOPE_BASE_URL.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                    ],
                }
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=settings.AI_TIMEOUT) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message") or {}
            return message.get("content", "")


class AITaggingService:
    """AI analysis service with provider selection and fallback."""

    def __init__(
        self,
        provider_name: str | None = None,
        model_id: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        self.enabled = settings.AI_ENABLED if enabled is None else enabled
        self.ollama_url = settings.OLLAMA_API_URL
        self.model_name = model_id or settings.AI_MODEL_ID or settings.AI_MODEL_NAME
        selected_provider = provider_name or settings.AI_PROVIDER
        self.primary_provider = self._create_provider(selected_provider)
        self.fallback_provider = None
        if selected_provider != "ollama":
            self.fallback_provider = self._create_provider("ollama")

    def _create_provider(self, provider_name: str) -> BaseAIProvider:
        if provider_name == "dashscope":
            provider = DashScopeVLMProvider()
        else:
            provider = OllamaProvider()
        provider.model_override = self.model_name
        return provider

    def _compress_and_encode_image(self, image_path: str, max_size: int = 1024) -> str:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            width, height = img.size
            if max(width, height) > max_size:
                ratio = max_size / max(width, height)
                img = img.resize((int(width * ratio), int(height * ratio)), Image.Resampling.LANCZOS)

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def _build_prompt(self) -> str:
        return (
            "你是校园媒体图库审核助手。请分析这张图片并只返回 JSON。"
            "请输出以下字段："
            "summary(一句中文概述), "
            "classifications(对象，键固定为 season/campus/building/gallery_series/gallery_year/photo_type), "
            "free_tags(数组，最多 10 个中文标签), "
            "quality_flags(数组，可含 模糊/过曝/欠曝/构图杂乱/疑似重复), "
            "risk_flags(数组，可含 含人物/证件信息/屏幕内容/敏感文本), "
            "confidence(0 到 1 的数字)。"
            "如果某个分类无法判断则填 null。"
            "season 优先用 春季/夏季/秋季/冬季，"
            "photo_type 优先用 风光/人像/活动/纪实。"
        )

    def _normalize_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = json.loads(json.dumps(DEFAULT_RESULT))
        if isinstance(payload.get("summary"), str):
            result["summary"] = payload["summary"].strip()

        classifications = payload.get("classifications") or {}
        if isinstance(classifications, dict):
            for key in result["classifications"]:
                value = classifications.get(key)
                if value is None:
                    continue
                result["classifications"][key] = str(value).strip() or None

        for key in ("free_tags", "quality_flags", "risk_flags"):
            values = payload.get(key)
            if isinstance(values, list):
                result[key] = [str(item).strip() for item in values if str(item).strip()][:10]

        confidence = payload.get("confidence")
        try:
            result["confidence"] = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            result["confidence"] = 0.0

        return result

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        text = (response_text or "").strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if not text:
            return json.loads(json.dumps(DEFAULT_RESULT))

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("AI response must be a JSON object.")
            return self._normalize_result(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse AI response: %s", exc)
            return json.loads(json.dumps(DEFAULT_RESULT))

    async def analyze_image(self, image_path: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            logger.info("AI service disabled. Skipping image analysis.")
            return None

        image_base64 = self._compress_and_encode_image(image_path)
        prompt = self._build_prompt()
        providers = [self.primary_provider]
        if self.fallback_provider:
            providers.append(self.fallback_provider)

        last_error: Optional[Exception] = None
        for provider in providers:
            for _attempt in range(settings.AI_MAX_RETRIES + 1):
                try:
                    response_text = await provider.analyze(image_base64, prompt)
                    result = self._parse_response(response_text)
                    result["provider"] = provider.provider_name
                    result["model_id"] = provider.model_id
                    return result
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning("AI provider %s failed: %s", provider.provider_name, exc)

        if last_error:
            logger.error("All AI providers failed: %s", last_error)
        return None


ai_service = AITaggingService()


async def analyze_photo_with_ai(image_path: str) -> Optional[dict[str, Any]]:
    """Convenience wrapper for legacy callers."""
    return await ai_service.analyze_image(image_path)


async def analyze_photo_with_runtime_settings(
    image_path: str,
    provider_name: str,
    model_id: str,
    enabled: bool,
) -> Optional[dict[str, Any]]:
    """Run AI analysis with DB-backed runtime overrides."""
    service = AITaggingService(provider_name=provider_name, model_id=model_id, enabled=enabled)
    return await service.analyze_image(image_path)
