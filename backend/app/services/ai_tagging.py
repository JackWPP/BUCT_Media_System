"""
AI analysis services with provider abstraction and fallback.
"""
from __future__ import annotations

import base64
import io
import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from PIL import Image

from app.services.ai_providers import ResolvedAIProvider

logger = logging.getLogger(__name__)


DEFAULT_RESULT = {
    "summary": "",
    "classifications": {
        "season": None,
        "campus": None,
        "landmark": None,
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

    def __init__(self, config: ResolvedAIProvider) -> None:
        self.config = config

    @property
    def provider_name(self) -> str:
        return self.config.provider_type

    @property
    def model_id(self) -> str:
        return self.config.model_id

    @property
    def timeout_seconds(self) -> int:
        return self.config.timeout_seconds

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        if self.config.extra_headers:
            headers.update({str(k): str(v) for k, v in self.config.extra_headers.items()})
        return headers

    @abstractmethod
    async def analyze(self, image_base64: str, prompt: str) -> str:
        raise NotImplementedError

    async def analyze_text(self, prompt: str) -> str:
        raise NotImplementedError


class OllamaProvider(BaseAIProvider):
    async def analyze(self, image_base64: str, prompt: str) -> str:
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.config.base_url.rstrip('/')}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def analyze_text(self, prompt: str) -> str:
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "stream": False,
        }
        text_timeout = min(self.timeout_seconds, 15)
        async with httpx.AsyncClient(timeout=text_timeout) as client:
            response = await client.post(f"{self.config.base_url.rstrip('/')}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")


class OpenAICompatibleProvider(BaseAIProvider):
    async def analyze(self, image_base64: str, prompt: str) -> str:
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
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message") or {}
            content = message.get("content", "")
            if isinstance(content, list):
                texts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
                return "\n".join(filter(None, texts))
            return str(content)

    async def analyze_text(self, prompt: str) -> str:
        payload = {
            "model": self.model_id,
            "messages": [
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
        }
        text_timeout = min(self.timeout_seconds, 15)
        async with httpx.AsyncClient(timeout=text_timeout) as client:
            response = await client.post(
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            if not choices:
                return ""
            message = choices[0].get("message") or {}
            content = message.get("content", "")
            if isinstance(content, list):
                texts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
                return "\n".join(filter(None, texts))
            return str(content)


class DashScopeVLMProvider(OpenAICompatibleProvider):
    """DashScope compatible-mode provider."""


class AITaggingService:
    """AI analysis service with provider selection and fallback."""

    def __init__(self, providers: list[ResolvedAIProvider], enabled: bool) -> None:
        self.providers = providers
        self.enabled = enabled

    @staticmethod
    def _create_provider(config: ResolvedAIProvider) -> BaseAIProvider:
        if config.provider_type == "ollama":
            return OllamaProvider(config)
        if config.provider_type == "dashscope":
            return DashScopeVLMProvider(config)
        return OpenAICompatibleProvider(config)

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

    @staticmethod
    def _build_prompt(context: dict[str, Any] | None = None) -> str:
        from app.prompts.photo_analysis import get_prompt
        return get_prompt(version="v3", context=context)

    @staticmethod
    def _normalize_result(payload: dict[str, Any]) -> dict[str, Any]:
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

    async def analyze_image(self, image_path: str, context: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not self.enabled or not self.providers:
            logger.info("AI service disabled or no provider available. Skipping image analysis.")
            return None

        image_base64 = self._compress_and_encode_image(image_path)
        prompt = self._build_prompt(context=context)
        last_error: Exception | None = None

        for provider_config in self.providers:
            provider = self._create_provider(provider_config)
            attempts = max(provider_config.max_retries, 0) + 1
            for _ in range(attempts):
                try:
                    response_text = await provider.analyze(image_base64, prompt)
                    result = self._parse_response(response_text)
                    result["provider"] = provider.provider_name
                    result["model_id"] = provider.model_id
                    return result
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning("AI provider %s failed: %s", provider.provider_name, exc)
                    break

        if last_error:
            logger.error("All AI providers failed: %s", last_error)
        return None


async def analyze_photo_with_runtime_settings(
    image_path: str,
    providers: list[ResolvedAIProvider],
    enabled: bool,
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run AI analysis with resolved runtime provider settings."""
    service = AITaggingService(providers=providers, enabled=enabled)
    return await service.analyze_image(image_path, context=context)
