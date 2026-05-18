from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

VALID_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

AWARD_LEVEL_MAP = {
    "1.特等奖": "特等奖",
    "2.一等奖": "一等奖",
    "3.二等奖": "二等奖",
    "4.优秀奖": "优秀奖",
}

SKIP_FILE_PATTERNS = (
    re.compile(r"^企业微信截图_", re.IGNORECASE),
    re.compile(r"^~\$"),
)

IMPORT_NAMESPACE = uuid.UUID("4f430f5a-5ef0-4f40-a55a-25efea520825")


@dataclass(frozen=True)
class CompetitionImportRecord:
    source_path: Path
    relative_path: Path
    filename: str
    stem: str
    extension: str
    entry_number: int | None
    title: str | None
    author: str | None
    award_level: str | None
    photo_type: str
    gallery_year: str
    gallery_series: str = "昌平校区摄影大赛"
    campus: str = "昌平校区"

    @property
    def source_key(self) -> str:
        return self.relative_path.as_posix()

    @property
    def photo_uuid(self) -> str:
        return str(uuid.uuid5(IMPORT_NAMESPACE, self.source_key))


def is_supported_image(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VALID_IMAGE_EXTENSIONS


def should_skip_file(path: Path) -> bool:
    filename = path.name.strip()
    return any(pattern.search(filename) for pattern in SKIP_FILE_PATTERNS)


def normalize_author(author: str | None) -> str | None:
    if not author:
        return None
    clean = author.strip().strip("—- ").strip()
    if not clean or clean in {"不署名", "匿名"}:
        return None
    return clean


def infer_award_level(parent_dir_name: str) -> str | None:
    return AWARD_LEVEL_MAP.get(parent_dir_name.strip())


def parse_entry_number(stem: str) -> tuple[int | None, str]:
    match = re.match(r"^(?P<num>\d+)[.\-]?\s*(?P<rest>.+)$", stem.strip())
    if not match:
        return None, stem.strip()
    return int(match.group("num")), match.group("rest").strip()


def parse_title_and_author(rest: str) -> tuple[str | None, str | None]:
    normalized = rest.strip()

    quoted = re.search(r'[“”"](?P<title>.+?)[“”"]', normalized)
    if quoted:
        title = quoted.group("title").strip()
        suffix = normalized[quoted.end():].strip()
        author_match = re.search(r"[（(](?P<author>.+?)[）)]", suffix)
        author = normalize_author(author_match.group("author")) if author_match else None
        return title or None, author

    author_match = re.search(r"[（(](?P<author>.+?)[）)]$", normalized)
    if author_match:
        author = normalize_author(author_match.group("author"))
        title = normalized[:author_match.start()].strip(" -—_")
        return title or None, author

    if "——" in normalized:
        parts = [part.strip() for part in normalized.split("——") if part.strip()]
        if len(parts) >= 2:
            title = parts[-2]
            author = normalize_author(parts[-1])
            return title or None, author

    if "-" in normalized:
        head, tail = normalized.rsplit("-", 1)
        title = head.strip()
        author = normalize_author(tail)
        if title:
            return title, author

    return normalized or None, None


def build_description(record: CompetitionImportRecord) -> str:
    parts: list[str] = []
    if record.title:
        parts.append(record.title)
    if record.author:
        parts.append(f"作者：{record.author}")
    parts.append("第八届昌平校区摄影大赛")
    if record.photo_type:
        parts.append(record.photo_type)
    if record.award_level:
        parts.append(record.award_level)
    if record.entry_number is not None:
        parts.append(f"序号：{record.entry_number}")
    return " | ".join(parts)


def build_classification_values(record: CompetitionImportRecord) -> dict[str, str]:
    values = {
        "campus": record.campus,
        "gallery_series": record.gallery_series,
        "gallery_year": record.gallery_year,
        "photo_type": record.photo_type,
    }
    if record.award_level:
        values["award_level"] = record.award_level
    return values


def parse_competition_record(
    source_path: Path,
    root_dir: Path,
    *,
    photo_type: str,
    gallery_year: str,
) -> CompetitionImportRecord:
    relative_path = source_path.resolve().relative_to(root_dir.resolve())
    stem = source_path.stem.strip()
    entry_number, rest = parse_entry_number(stem)
    title, author = parse_title_and_author(rest)
    return CompetitionImportRecord(
        source_path=source_path,
        relative_path=relative_path,
        filename=source_path.name,
        stem=stem,
        extension=source_path.suffix.lower(),
        entry_number=entry_number,
        title=title,
        author=author,
        award_level=infer_award_level(source_path.parent.name),
        photo_type=photo_type,
        gallery_year=gallery_year,
    )


def scan_competition_directory(
    root_dir: Path,
    *,
    photo_type: str,
    gallery_year: str,
) -> list[CompetitionImportRecord]:
    records: list[CompetitionImportRecord] = []
    for path in sorted(root_dir.rglob("*")):
        if not is_supported_image(path) or should_skip_file(path):
            continue
        records.append(
            parse_competition_record(
                path,
                root_dir,
                photo_type=photo_type,
                gallery_year=gallery_year,
            )
        )
    return records
