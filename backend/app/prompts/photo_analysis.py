"""
Photo analysis prompt templates.

Versioned prompt templates for AI-based photo classification.
Each version is a Python constant for easy version control and review.

Usage:
    from app.prompts.photo_analysis import get_prompt

    prompt = get_prompt("v3", context={"photo_type": "风光", "gallery_year": "2020"})
"""
from __future__ import annotations

import json
from typing import Any

# ---------------------------------------------------------------------------
# v3: Structured prompt with few-shot examples and strict enum constraints
# ---------------------------------------------------------------------------

PROMPT_V3 = """\
你是北京化工大学校园媒体图库的分类标注助手。
你的任务是根据照片内容，返回结构化的 JSON 分类结果。
严格遵守下面的输出格式和枚举值，不要自行创造新的分类值。
你必须只输出纯 JSON 对象，以 { 字符开始、以 } 字符结束。不要包裹在 markdown 代码块中，不要添加任何解释文字。

## 判断指南
- 观察植被状态判断季节：绿叶茂盛→夏季，银杏黄叶/红叶→秋季，枯枝/雪景→冬季，樱花/新绿→春季
- 识别建筑特征判断地标：圆形玻璃建筑→图书馆，红砖建筑→学生活动中心，有钟楼的→主楼
- 若照片中有大量人物且以人为主体→人像，若记录事件/活动过程→纪实，若以自然或建筑为主→风光
- 若完全无法判断某个字段，填 null，不要编造

## 返回格式

{
  "summary": "一句话中文描述照片内容（15-30字）",
  "classifications": {
    "season": "春季|夏季|秋季|冬季|null",
    "campus": "昌平校区|朝阳校区|null",
    "landmark": "见下方地标列表|null",
    "gallery_series": "摄影大赛|校园风光|活动纪实|null",
    "gallery_year": "2018-2025|null",
    "photo_type": "风光|人像|活动|纪实|null"
  },
  "free_tags": ["标签1", "标签2"],
  "quality_flags": [],
  "risk_flags": [],
  "confidence": 0.85
}

## 枚举值约束

只允许以下值，无法判断时填 null：

- season: 春季、夏季、秋季、冬季
- campus: 昌平校区、朝阳校区
- landmark: 北化昌平校区常见地标（如果不在列表中，返回你认为最准确的名称）：
  图书馆、一教、二教、三教、实验楼、行政楼、体育馆、学生活动中心、樱花苑学生公寓、主楼、科技大厦、柳湖、樱花大道、操场、校门、主楼广场
- gallery_series: 摄影大赛、校园风光、活动纪实
- gallery_year: 2018 到 2025 的年份数字字符串
- photo_type: 风光、人像、活动、纪实

## 常见错误避免

- ❌ "春天" → ✅ "春季"
- ❌ "风景"/"风景照" → ✅ "风光"
- ❌ "记录" → ✅ "纪实"
- ❌ "校园" 作为 campus → ✅ "昌平校区" 或 "朝阳校区"
- ❌ 返回英文值 → ✅ 所有分类值使用中文

## 示例

示例1（校园风光-秋季图书馆）：
{
  "summary": "秋季图书馆门前银杏落叶，学生在台阶上阅读",
  "classifications": {
    "season": "秋季", "campus": "昌平校区", "landmark": "图书馆",
    "gallery_series": "校园风光", "gallery_year": null, "photo_type": "风光"
  },
  "free_tags": ["银杏", "图书馆", "秋天", "阳光", "校园", "落叶"],
  "quality_flags": [],
  "risk_flags": ["含人物"],
  "confidence": 0.92
}

示例2（纪实活动-实验课）：
{
  "summary": "学生身穿实验服在实验楼进行化学实验操作",
  "classifications": {
    "season": null, "campus": "昌平校区", "landmark": "实验楼",
    "gallery_series": "活动纪实", "gallery_year": null, "photo_type": "纪实"
  },
  "free_tags": ["化学实验", "实验课", "学生", "实验服"],
  "quality_flags": [],
  "risk_flags": ["含人物"],
  "confidence": 0.78
}

示例3（摄影大赛-柳湖春景）：
{
  "summary": "柳湖樱花倒影，远处教学楼轮廓清晰",
  "classifications": {
    "season": "春季", "campus": "昌平校区", "landmark": "柳湖",
    "gallery_series": "摄影大赛", "gallery_year": null, "photo_type": "风光"
  },
  "free_tags": ["柳湖", "樱花", "倒影", "水面", "教学楼", "春景"],
  "quality_flags": [],
  "risk_flags": [],
  "confidence": 0.88
}"""

PROMPT_V3_CONTEST = """\
你是北京化工大学校园媒体图库的分类标注助手。
你正在分析北京化工大学昌平校区摄影大赛的参赛照片。
你必须只输出纯 JSON 对象，以 {{ 字符开始、以 }} 字符结束。不要包裹在 markdown 代码块中，不要添加任何解释文字。

以下信息已经从照片元数据中获知，你不需要再判断，请直接填入对应位置：
- campus: 昌平校区
- gallery_series: 摄影大赛
- gallery_year: {gallery_year}
- photo_type: {photo_type}

将你的分析能力集中在：
1. season（季节）的判断
2. landmark（是否包含可识别的校园建筑/地标）
3. summary（对照片内容的简洁描述，突出构图和意境）
4. free_tags（场景、元素、氛围、构图方式等描述性标签）

## 判断指南
- 观察植被状态判断季节：绿叶茂盛→夏季，银杏黄叶/红叶→秋季，枯枝/雪景→冬季，樱花/新绿→春季
- 识别建筑特征判断地标：圆形玻璃建筑→图书馆，红砖建筑→学生活动中心，有钟楼的→主楼
- 若完全无法判断某个字段，填 null，不要编造

## 返回格式

{{
  "summary": "一句话中文描述照片内容（15-30字）",
  "classifications": {{
    "season": "春季|夏季|秋季|冬季|null",
    "campus": "昌平校区",
    "landmark": "见下方地标列表|null",
    "gallery_series": "摄影大赛",
    "gallery_year": "{gallery_year}",
    "photo_type": "{photo_type}"
  }},
  "free_tags": ["标签1", "标签2"],
  "quality_flags": [],
  "risk_flags": [],
  "confidence": 0.85
}}

## 枚举值约束

- season: 春季、夏季、秋季、冬季
- landmark: 北化昌平校区常见地标（如果不在列表中，返回你认为最准确的名称）：
  图书馆、一教、二教、三教、实验楼、行政楼、体育馆、学生活动中心、樱花苑学生公寓、主楼、科技大厦、柳湖、樱花大道、操场、校门、主楼广场

## 常见错误避免

- ❌ "春天" → ✅ "春季"
- ❌ "风景"/"风景照" → ✅ "风光"
- ❌ "记录" → ✅ "纪实"
- ❌ 返回英文值 → ✅ 所有分类值使用中文

## 示例

示例1（摄影大赛-风光-柳湖春景）：
{{
  "summary": "柳湖樱花倒影，远处教学楼轮廓清晰",
  "classifications": {{
    "season": "春季", "campus": "昌平校区", "landmark": "柳湖",
    "gallery_series": "摄影大赛", "gallery_year": "{gallery_year}", "photo_type": "风光"
  }},
  "free_tags": ["柳湖", "樱花", "倒影", "水面", "教学楼", "春景"],
  "quality_flags": [],
  "risk_flags": [],
  "confidence": 0.88
}}

示例2（摄影大赛-纪实-校园活动）：
{{
  "summary": "学生在实验楼内进行化学实验操作，专注观察反应",
  "classifications": {{
    "season": null, "campus": "昌平校区", "landmark": "实验楼",
    "gallery_series": "摄影大赛", "gallery_year": "{gallery_year}", "photo_type": "纪实"
  }},
  "free_tags": ["化学实验", "实验课", "学生", "实验服"],
  "quality_flags": [],
  "risk_flags": ["含人物"],
  "confidence": 0.82
}}"""

# ---------------------------------------------------------------------------
# Prompt registry and selector
# ---------------------------------------------------------------------------

PROMPTS: dict[str, str] = {
    "v3": PROMPT_V3,
    "v3_contest": PROMPT_V3_CONTEST,
}

# Context keys that indicate a contest photo
_CONTEST_CONTEXT_KEYS = {"gallery_series", "gallery_year", "photo_type"}


def get_prompt(version: str = "v3", context: dict[str, Any] | None = None) -> str:
    """Return the prompt text for the given version and context.

    If context contains contest-related keys (gallery_series, gallery_year, photo_type),
    the contest-specific prompt variant is used. Otherwise the generic prompt is returned.

    For the contest prompt, context must contain at least "gallery_year" and "photo_type".
    """
    context = context or {}

    # Determine if this is a contest photo
    is_contest = bool(_CONTEST_CONTEXT_KEYS & set(context.keys()))

    if is_contest and version == "v3":
        template = PROMPT_V3_CONTEST
        # Format the contest prompt with known context values
        gallery_year = context.get("gallery_year", "null")
        photo_type = context.get("photo_type", "风光")
        return template.format(
            gallery_year=gallery_year,
            photo_type=photo_type,
        )

    # Fall back to version lookup
    return PROMPTS.get(version, PROMPT_V3)
