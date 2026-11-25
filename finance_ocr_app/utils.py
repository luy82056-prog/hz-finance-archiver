from __future__ import annotations

import re
import shutil
from pathlib import Path

from .models import SUPPORTED_EXTENSIONS


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def iter_supported_files(paths: list[Path]) -> list[Path]:
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                    found.append(child)
        elif path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            found.append(path)
    return sorted(dict.fromkeys(found))


def safe_name(value: str, default: str = "未命名") -> str:
    value = (value or "").strip() or default
    value = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:80] or default


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def copy_file_unique(src: Path, dest_dir: Path) -> Path:
    ensure_dir(dest_dir)
    dest = unique_path(dest_dir / src.name)
    shutil.copy2(src, dest)
    return dest


def normalize_date_for_path(date_text: str) -> tuple[str, str]:
    match = re.search(r"(?P<year>20\d{2}|19\d{2})[年./-]?\s*(?P<month>\d{1,2})?", date_text or "")
    if not match:
        return "未知年份", "未知月份"
    year = match.group("year")
    month = match.group("month")
    return year, f"{int(month):02d}" if month else "未知月份"
