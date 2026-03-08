from pathlib import Path

import pytest
from PIL import Image

from app.services.ai_providers import ResolvedAIProvider
from app.services.ai_tagging import AITaggingService


def create_test_image(path: Path) -> None:
    image = Image.new("RGB", (32, 32), color=(240, 240, 240))
    image.save(path, format="JPEG")


def test_parse_response_normalizes_payload():
    service = AITaggingService(providers=[], enabled=True)

    payload = service._parse_response(
        """
        ```json
        {
          "summary": "校园冬景",
          "classifications": {"season": "冬季", "photo_type": "风光"},
          "free_tags": ["雪景", "教学楼"],
          "quality_flags": ["模糊"],
          "risk_flags": [],
          "confidence": 0.82
        }
        ```
        """
    )

    assert payload["summary"] == "校园冬景"
    assert payload["classifications"]["season"] == "冬季"
    assert payload["classifications"]["photo_type"] == "风光"
    assert payload["free_tags"] == ["雪景", "教学楼"]
    assert payload["quality_flags"] == ["模糊"]
    assert payload["confidence"] == 0.82


@pytest.mark.asyncio
async def test_service_falls_back_to_second_provider(monkeypatch, tmp_path: Path):
    image_path = tmp_path / "sample.jpg"
    create_test_image(image_path)

    providers = [
        ResolvedAIProvider(
            provider_type="dashscope",
            display_name="Primary",
            base_url="https://primary.example.com",
            model_id="model-a",
            api_key="secret",
            extra_headers={},
            timeout_seconds=5,
            max_retries=0,
            daily_budget=100,
            source="db",
            provider_id="primary",
        ),
        ResolvedAIProvider(
            provider_type="ollama",
            display_name="Fallback",
            base_url="http://localhost:11434",
            model_id="llava",
            api_key=None,
            extra_headers={},
            timeout_seconds=5,
            max_retries=0,
            daily_budget=100,
            source="db",
            provider_id="fallback",
        ),
    ]

    class FailingProvider:
        provider_name = "dashscope"
        model_id = "model-a"

        async def analyze(self, image_base64: str, prompt: str) -> str:
            raise RuntimeError("boom")

    class SuccessProvider:
        provider_name = "ollama"
        model_id = "llava"

        async def analyze(self, image_base64: str, prompt: str) -> str:
            return '{"summary":"ok","classifications":{"photo_type":"风光"},"free_tags":["校园"],"quality_flags":[],"risk_flags":[],"confidence":0.9}'

    def fake_create_provider(config: ResolvedAIProvider):
        return FailingProvider() if config.provider_type == "dashscope" else SuccessProvider()

    monkeypatch.setattr(AITaggingService, "_create_provider", staticmethod(fake_create_provider))

    service = AITaggingService(providers=providers, enabled=True)
    result = await service.analyze_image(str(image_path))

    assert result is not None
    assert result["provider"] == "ollama"
    assert result["model_id"] == "llava"
    assert result["classifications"]["photo_type"] == "风光"
