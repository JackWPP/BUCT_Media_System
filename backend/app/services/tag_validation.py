"""
Tag validation, cleaning, and quality assessment.

Phase 2A.1: Tag system improvement — validates and normalizes AI-generated
tags before they enter the database, and provides quality metrics.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tag category definitions
# ---------------------------------------------------------------------------

TAG_CATEGORIES = {
    "scene": {
        "name": "场景",
        "description": "拍摄地点或场景类型",
        "examples": ["校园", "教室", "图书馆", "实验室", "操场", "宿舍", "食堂"],
    },
    "object": {
        "name": "物体",
        "description": "画面中的主要物体或元素",
        "examples": ["银杏", "樱花", "教学楼", "自行车", "书本", "篮球"],
    },
    "mood": {
        "name": "情绪",
        "description": "照片传达的情绪或氛围",
        "examples": ["宁静", "活力", "庄严", "温馨", "欢快", "肃穆"],
    },
    "color": {
        "name": "颜色",
        "description": "画面中的主要色调",
        "examples": ["金黄", "翠绿", "火红", "湛蓝", "洁白", "暖橙"],
    },
    "style": {
        "name": "风格",
        "description": "摄影风格或构图方式",
        "examples": ["航拍", "特写", "逆光", "对称", "远景", "剪影", "延时"],
    },
    "activity": {
        "name": "活动",
        "description": "画面中正在进行的活动",
        "examples": ["上课", "实验", "运动", "阅读", "拍照", "散步"],
    },
    "time": {
        "name": "时间",
        "description": "拍摄时间或时间段",
        "examples": ["清晨", "黄昏", "傍晚", "正午", "夜晚"],
    },
    "weather": {
        "name": "天气",
        "description": "天气状况",
        "examples": ["晴天", "阴天", "雨后", "雪景", "雾霭", "晚霞"],
    },
}

# Minimum quality thresholds
MIN_TAG_LENGTH = 1
MAX_TAG_LENGTH = 20
MAX_TAGS_PER_PHOTO = 15
MIN_CONFIDENCE_FOR_AUTO_APPLY = 0.7

# Tags that are too generic / useless for search
_NOISE_TAGS = frozenset({
    "照片", "图片", "摄影", "拍摄", "校园", "北化", "北京化工大学",
    "photo", "image", "picture",
})

# Common missynonyms and normalizations
_TAG_SYNONYMS: dict[str, str] = {
    "春天": "春季",
    "夏天": "夏季",
    "秋天": "秋季",
    "冬天": "冬季",
    "教学楼群": "教学楼",
    "主教学楼": "第一教学楼",
    "活动中心": "大学生活动中心",
    "学生活动中心": "大学生活动中心",
    "食堂": "紫竹餐厅",
    "夜景": "夜色",
    "蓝天": "晴空",
    "白云": "云彩",
}

# Regex for tags that are just numbers, single chars, or meaningless
_NOISE_PATTERN = re.compile(r"^[\d\s\W]+$|^[a-zA-Z]$")


@dataclass
class TagValidationResult:
    """Result of validating a single tag."""
    original: str
    cleaned: str | None = None
    is_valid: bool = False
    category: str | None = None
    issues: list[str] = field(default_factory=list)


@dataclass
class AnalysisValidationResult:
    """Result of validating an entire AI analysis result."""
    original_tags: list[str] = field(default_factory=list)
    cleaned_tags: list[str] = field(default_factory=list)
    removed_tags: list[str] = field(default_factory=list)
    normalized_tags: dict[str, str] = field(default_factory=dict)  # original → cleaned
    tag_categories: dict[str, str] = field(default_factory=dict)  # tag → category
    quality_score: float = 0.0
    issues: list[str] = field(default_factory=list)


def validate_single_tag(tag: str) -> TagValidationResult:
    """Validate and clean a single tag.

    Returns a TagValidationResult with the cleaned tag (if valid) and any issues.
    """
    result = TagValidationResult(original=tag)

    # Step 1: Basic cleaning
    cleaned = tag.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)  # collapse whitespace

    if not cleaned:
        result.issues.append("empty tag")
        return result

    # Step 2: Length check
    if len(cleaned) < MIN_TAG_LENGTH:
        result.issues.append(f"too short ({len(cleaned)} chars)")
        return result

    if len(cleaned) > MAX_TAG_LENGTH:
        # Truncate at word boundary
        cleaned = cleaned[:MAX_TAG_LENGTH].rstrip()
        result.issues.append(f"truncated to {MAX_TAG_LENGTH} chars")

    # Step 3: Noise detection
    if _NOISE_PATTERN.match(cleaned):
        result.issues.append("matches noise pattern (numbers/symbols only)")
        return result

    if cleaned.lower() in _NOISE_TAGS:
        result.issues.append(f"'{cleaned}' is too generic/noisy")
        return result

    # Step 4: Synonym normalization
    normalized = _TAG_SYNONYMS.get(cleaned, cleaned)
    if normalized != cleaned:
        result.issues.append(f"normalized: '{cleaned}' → '{normalized}'")
        cleaned = normalized

    # Step 5: Remove trailing punctuation
    cleaned = re.sub(r"[，。、；：！？,.:;!?\s]+$", "", cleaned)
    if not cleaned:
        result.issues.append("empty after punctuation removal")
        return result

    result.cleaned = cleaned
    result.is_valid = True
    return result


def classify_tag(tag: str) -> str | None:
    """Attempt to classify a tag into a category using heuristics.

    This is a lightweight classifier — not ML-based, just keyword matching.
    Returns the category key or None if unclassified.
    """
    tag_lower = tag.lower()
    tag_len = len(tag)

    # Color keywords — precise matching to avoid false positives
    color_chars = {"红", "蓝", "绿", "黄", "白", "黑", "灰", "紫", "橙", "粉",
                   "金", "银", "翠", "碧", "青", "赤", "朱", "黛", "霞", "虹"}
    color_multi = {"暖色", "冷色", "色调", "色彩", "金黄", "翠绿", "火红", "湛蓝",
                   "洁白", "暖橙", "深紫", "银灰", "墨黑", "嫣红", "碧绿", "蔚蓝"}

    if tag_len <= 1:
        if tag_lower in color_chars:
            return "color"
    elif tag_len == 2:
        # For 2-char tags: both chars must be color chars, OR exact match in color_multi
        if tag in color_multi:
            return "color"
        if all(c in color_chars for c in tag):
            return "color"
    else:
        # For 3+ char tags: check multi-char color words as substring
        if any(w in tag for w in color_multi):
            return "color"

    # Mood keywords — exact match only
    mood_words = {
        "宁静", "活力", "庄严", "温馨", "欢快", "肃穆", "浪漫", "孤独",
        "热闹", "安详", "静谧", "明媚", "朦胧", "壮丽", "雅致", "古朴",
        "诗意", "恬静", "悠远",
    }
    if tag_lower in {w.lower() for w in mood_words}:
        return "mood"

    # Time keywords — exact match only
    time_words = {"清晨", "黄昏", "傍晚", "正午", "夜晚", "黎明", "日出", "日落", "午后"}
    if tag_lower in {w.lower() for w in time_words}:
        return "time"

    # Weather keywords — exact match or contains
    weather_words = {"晴天", "阴天", "雨后", "雪景", "雾霭", "晚霞", "朝霞", "彩虹", "云层"}
    if tag_lower in {w.lower() for w in weather_words}:
        return "weather"

    # Style keywords — exact match only
    style_words = {
        "航拍", "特写", "逆光", "对称", "远景", "剪影", "延时", "长曝光",
        "微距", "全景", "俯拍", "仰拍", "广角", "光影", "构图", "留白",
    }
    if tag_lower in {w.lower() for w in style_words}:
        return "style"

    # Activity keywords — exact match or contains for longer tags
    activity_words = {
        "上课", "实验", "运动", "阅读", "拍照", "散步", "跑步", "打球",
        "军训", "考试", "毕业", "开学", "典礼", "讲座", "讨论", "自习",
    }
    if tag_lower in {w.lower() for w in activity_words}:
        return "activity"

    # Scene keywords — exact match only
    scene_words = {
        "校园", "教室", "图书馆", "实验室", "操场", "宿舍", "食堂",
        "走廊", "大厅", "广场", "花园", "湖边", "山丘", "道路",
    }
    if tag_lower in {w.lower() for w in scene_words}:
        return "scene"

    # Default: assume object (most free-form tags are objects/elements)
    return "object"


def validate_analysis_result(result: dict[str, Any]) -> AnalysisValidationResult:
    """Validate and clean an entire AI analysis result.

    Processes the free_tags list: removes noise, normalizes, deduplicates,
    and assigns categories.

    Args:
        result: The AI analysis result dict (from AITaggingService)

    Returns:
        AnalysisValidationResult with cleaned tags and quality metrics
    """
    validation = AnalysisValidationResult()

    # Extract free_tags
    raw_tags = result.get("free_tags") or []
    if not isinstance(raw_tags, list):
        validation.issues.append("free_tags is not a list")
        return validation

    validation.original_tags = [str(t) for t in raw_tags]

    seen: set[str] = set()
    for raw_tag in raw_tags:
        tag_str = str(raw_tag).strip()
        if not tag_str:
            continue

        single_result = validate_single_tag(tag_str)

        if not single_result.is_valid:
            validation.removed_tags.append(tag_str)
            continue

        cleaned = single_result.cleaned
        assert cleaned is not None

        # Deduplicate (case-insensitive)
        if cleaned.lower() in seen:
            validation.removed_tags.append(tag_str)
            continue

        seen.add(cleaned.lower())
        validation.cleaned_tags.append(cleaned)
        validation.normalized_tags[tag_str] = cleaned

        # Classify
        category = classify_tag(cleaned)
        if category:
            validation.tag_categories[cleaned] = category

    # Enforce max tags limit
    if len(validation.cleaned_tags) > MAX_TAGS_PER_PHOTO:
        removed = validation.cleaned_tags[MAX_TAGS_PER_PHOTO:]
        validation.cleaned_tags = validation.cleaned_tags[:MAX_TAGS_PER_PHOTO]
        validation.removed_tags.extend(removed)
        validation.issues.append(f"trimmed to {MAX_TAGS_PER_PHOTO} tags")

    # Calculate quality score
    validation.quality_score = _calculate_quality_score(result, validation)

    return validation


def _calculate_quality_score(
    result: dict[str, Any],
    validation: AnalysisValidationResult,
) -> float:
    """Calculate a quality score (0.0-1.0) for the analysis result.

    Factors:
    - Number of valid tags (more = better, up to a point)
    - Tag diversity (different categories = better)
    - Confidence from AI
    - Summary quality (length, not empty)
    - Classification completeness
    """
    score = 0.0

    # Tag count (max 0.3)
    tag_count = len(validation.cleaned_tags)
    if tag_count >= 5:
        score += 0.3
    elif tag_count >= 3:
        score += 0.2
    elif tag_count >= 1:
        score += 0.1

    # Tag diversity (max 0.2)
    categories = set(validation.tag_categories.values())
    diversity = min(len(categories) / 4.0, 1.0)
    score += diversity * 0.2

    # AI confidence (max 0.25)
    confidence = result.get("confidence", 0.0)
    if isinstance(confidence, (int, float)):
        score += min(max(confidence, 0.0), 1.0) * 0.25

    # Summary quality (max 0.15)
    summary = result.get("summary", "")
    if isinstance(summary, str) and len(summary) >= 10:
        score += 0.15
    elif isinstance(summary, str) and len(summary) >= 5:
        score += 0.08

    # Classification completeness (max 0.1)
    classifications = result.get("classifications") or {}
    if isinstance(classifications, dict):
        filled = sum(1 for v in classifications.values() if v is not None)
        total = len(classifications)
        if total > 0:
            score += (filled / total) * 0.1

    return round(min(score, 1.0), 2)


def get_tag_quality_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Generate a quality report for a batch of analysis results.

    Useful for assessing overall tag quality across the photo library.

    Returns:
        Dict with aggregate metrics:
        - total_photos: number of photos analyzed
        - avg_quality_score: average quality score
        - total_tags: total number of valid tags
        - avg_tags_per_photo: average tags per photo
        - category_distribution: tag count per category
        - noise_rate: percentage of tags removed
        - top_issues: most common issues
    """
    total_photos = len(results)
    if total_photos == 0:
        return {"total_photos": 0}

    validations = [validate_analysis_result(r) for r in results]

    total_tags = sum(len(v.cleaned_tags) for v in validations)
    total_original = sum(len(v.original_tags) for v in validations)
    total_removed = sum(len(v.removed_tags) for v in validations)

    category_dist: dict[str, int] = {}
    for v in validations:
        for cat in v.tag_categories.values():
            category_dist[cat] = category_dist.get(cat, 0) + 1

    issue_counts: dict[str, int] = {}
    for v in validations:
        for issue in v.issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    return {
        "total_photos": total_photos,
        "avg_quality_score": round(
            sum(v.quality_score for v in validations) / total_photos, 2
        ),
        "total_tags": total_tags,
        "avg_tags_per_photo": round(total_tags / total_photos, 1),
        "category_distribution": dict(sorted(
            category_dist.items(), key=lambda x: x[1], reverse=True
        )),
        "noise_rate": round(
            total_removed / max(total_original, 1) * 100, 1
        ),
        "top_issues": dict(sorted(
            issue_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]),
    }
