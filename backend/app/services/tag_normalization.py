"""
Free-tag normalization and alias helpers.
"""
from __future__ import annotations

import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag, TagAlias

_SPACE_RE = re.compile(r"\s+")


def normalize_tag_name(name: str) -> str:
    """Normalize a free tag without over-merging distinct Chinese concepts."""
    normalized = unicodedata.normalize("NFKC", name or "")
    normalized = _SPACE_RE.sub(" ", normalized.strip())
    return normalized.lower()


async def resolve_tag_by_name_or_alias(db: AsyncSession, raw_name: str) -> Tag | None:
    clean = normalize_tag_name(raw_name)
    if not clean:
        return None

    result = await db.execute(select(Tag).where(func.lower(Tag.name) == clean))
    tag = result.scalar_one_or_none()
    if tag:
        return tag

    result = await db.execute(
        select(Tag)
        .join(TagAlias)
        .where(func.lower(TagAlias.alias) == clean)
    )
    return result.scalar_one_or_none()

