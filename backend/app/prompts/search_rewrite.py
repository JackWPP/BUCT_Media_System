"""
Prompt templates for AI-powered search query rewriting.

Dynamically builds prompts based on the current taxonomy schema,
so new facets/nodes/aliases are automatically supported without code changes.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from app.services.search_interpreter import SearchInterpretation

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
你是北京化工大学校园媒体图库的搜索意图识别助手。
你的任务是将用户的自然语言搜索请求解析为结构化的搜索参数。

你必须只输出纯 JSON 对象，以 { 字符开始、以 } 字符结束。不要包裹在 markdown 代码块中，不要添加任何解释文字。"""

_OUTPUT_SCHEMA = """\
## 输出格式

{
  "facet_filters": {"分类面key": "节点名称", ...},
  "keywords": ["剩余关键词1", "剩余关键词2"],
  "explanation": "简短中文解释（如：季节=秋季, 地标=图书馆, 关键词:银杏）"
}

- facet_filters: 从用户查询中提取的分类筛选，key 必须是下面的分类面 key，值必须是该分类面下存在的节点名称
- keywords: 无法归入任何分类面的剩余搜索关键词
- explanation: 一句话中文解释你的理解结果
- 如果某个分类面无法判断，不要放入 facet_filters
- 如果查询中没有剩余关键词，keywords 为空数组"""

_RULES = """\
## 规则

1. 优先将用户查询中的词映射到分类面节点
2. 同义词也要识别（如"春天"→"春季"，"风景"→"风光"）
3. 无法归入分类面的词保留为 keywords
4. 不要编造分类值，只使用下面列出的节点名称
5. 如果整个查询无法解析，返回空的 facet_filters 和原查询作为 keywords"""


def build_search_rewrite_prompt(query: str, taxonomy_schema: dict[str, Any]) -> str:
    taxonomy_desc = "## 可用分类面\n\n"
    for facet_key, facet_info in taxonomy_schema.items():
        facet_name = facet_info.get("name", facet_key)
        nodes = facet_info.get("nodes", [])
        if nodes:
            nodes_str = "、".join(nodes)
            taxonomy_desc += f"- **{facet_key}**（{facet_name}）: {nodes_str}\n"
        else:
            taxonomy_desc += f"- **{facet_key}**（{facet_name}）: （无预定义节点）\n"

    taxonomy_desc += "\n## 用户搜索请求\n\n" + query

    return f"{_SYSTEM_PROMPT}\n\n{_OUTPUT_SCHEMA}\n\n{_RULES}\n\n{taxonomy_desc}"


def parse_rewrite_response(
    response_text: str,
    original_query: str,
    taxonomy_schema: dict[str, Any],
) -> SearchInterpretation | None:
    text = (response_text or "").strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    if not text:
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse AI rewrite response as JSON")
        return None

    if not isinstance(data, dict):
        return None

    facet_filters_raw = data.get("facet_filters") or {}
    keywords_raw = data.get("keywords") or []
    explanation = data.get("explanation")

    if not isinstance(facet_filters_raw, dict) or not isinstance(keywords_raw, list):
        return None

    validated_filters: dict[str, str] = {}
    for facet_key, node_name in facet_filters_raw.items():
        if not isinstance(facet_key, str) or not isinstance(node_name, str):
            continue
        if facet_key not in taxonomy_schema:
            continue
        allowed_nodes = taxonomy_schema[facet_key].get("nodes", [])
        if node_name in allowed_nodes:
            validated_filters[facet_key] = node_name
        else:
            for allowed in allowed_nodes:
                if allowed.lower() == node_name.lower():
                    validated_filters[facet_key] = allowed
                    break

    validated_keywords = [str(k).strip() for k in keywords_raw if str(k).strip()]

    if not validated_filters and not validated_keywords:
        return None

    confidence = 0.6
    if validated_filters:
        confidence = min(0.9, 0.6 + len(validated_filters) * 0.1)

    return SearchInterpretation(
        facet_filters=validated_filters,
        keywords=validated_keywords,
        original_query=original_query,
        method="ai",
        confidence=confidence,
        explanation=explanation,
        ai_raw_response=data,
    )
