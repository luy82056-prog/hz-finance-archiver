from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    if base.name != "finance_ocr_app":
        candidate = base / "finance_ocr_app" / relative_path
        if candidate.exists():
            return candidate
    return base / relative_path


def app_icon_png() -> Path:
    return resource_path("assets/app_icon.png")


def app_icon_256() -> Path:
    return resource_path("assets/app_icon_256.png")
