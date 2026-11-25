from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


FIELD_MAP = {
    "party": "party",
    "date": "date",
    "document_number": "document_number",
    "amount": "amount",
    "tax_amount": "tax_amount",
    "tax_rate": "tax_rate",
    "currency": "currency",
    "project": "project",
}


@dataclass
class ExtractionTemplate:
    name: str
    document_type: str
    keywords: list[str] = field(default_factory=list)
    fields: dict[str, list[str]] = field(default_factory=dict)
    min_score: float = 0.15

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ExtractionTemplate":
        fields = {
            name: patterns if isinstance(patterns, list) else [str(patterns)]
            for name, patterns in (raw.get("fields") or {}).items()
        }
        return cls(
            name=str(raw.get("name") or raw.get("document_type") or "未命名模板"),
            document_type=str(raw.get("document_type") or "未知"),
            keywords=[str(v) for v in raw.get("keywords", [])],
            fields=fields,
            min_score=float(raw.get("min_score", 0.15)),
        )

    def score(self, text: str) -> float:
        if not self.keywords:
            return 0.0
        lower = text.lower()
        hits = sum(1 for keyword in self.keywords if keyword.lower() in lower)
        return hits / max(len(self.keywords), 1)

    def extract(self, text: str) -> tuple[dict[str, str], float]:
        values: dict[str, str] = {}
        matched = 0
        total = max(len(self.fields), 1)
        for field_name, patterns in self.fields.items():
            for pattern in patterns:
                match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
                if match:
                    value = next((g for g in match.groups() if g), match.group(0))
                    values[FIELD_MAP.get(field_name, field_name)] = clean_value(value)
                    matched += 1
                    break
        keyword_score = self.score(text)
        field_score = matched / total
        confidence = min(1.0, keyword_score * 0.45 + field_score * 0.55)
        return values, confidence


def clean_value(value: str) -> str:
    value = re.sub(r"[\u3000\t]+", " ", value or "")
    value = value.strip(" ：:，,;；\n\r")
    return value.strip()


def load_templates(template_dir: Path) -> list[ExtractionTemplate]:
    templates: list[ExtractionTemplate] = []
    for path in sorted(template_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        if isinstance(raw, list):
            templates.extend(ExtractionTemplate.from_dict(item) for item in raw)
        else:
            templates.append(ExtractionTemplate.from_dict(raw))
    return templates


def choose_template(text: str, templates: list[ExtractionTemplate]) -> ExtractionTemplate | None:
    scored = sorted(((template.score(text), template) for template in templates), key=lambda x: x[0], reverse=True)
    if not scored or scored[0][0] < scored[0][1].min_score:
        return None
    return scored[0][1]
