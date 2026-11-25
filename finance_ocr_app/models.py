from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".docx"}
WORD_EXTENSIONS = {".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
OUTPUT_EXTENSIONS = {".xlsx", ".docx"}


@dataclass
class ExtractedTable:
    rows: list[list[str]]
    source: str = ""


@dataclass
class DocumentFields:
    filename: str
    document_type: str = "未知"
    party: str = ""
    date: str = ""
    document_number: str = ""
    amount: str = ""
    tax_amount: str = ""
    tax_rate: str = ""
    currency: str = "CNY"
    project: str = ""
    confidence: float = 0.0
    archive_path: str = ""
    status: str = "待处理"
    notes: str = ""

    def as_ledger_row(self) -> dict[str, Any]:
        return {
            "文件名": self.filename,
            "文档类型": self.document_type,
            "供应商/对方户名": self.party,
            "日期": self.date,
            "发票号/流水号": self.document_number,
            "金额": self.amount,
            "税额": self.tax_amount,
            "税率": self.tax_rate,
            "币种": self.currency,
            "项目名": self.project,
            "项目名称": self.project,
            "价税合计": self.amount,
            "真实价格": self.amount,
            "识别置信度": round(self.confidence, 3),
            "归档路径": self.archive_path,
            "处理状态": self.status,
            "备注": self.notes,
        }


@dataclass
class ProcessResult:
    source_path: Path
    working_path: Path | None = None
    text: str = ""
    fields: DocumentFields | None = None
    tables: list[ExtractedTable] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def ok(self) -> bool:
        return self.fields is not None and not self.errors


@dataclass
class AppSettings:
    output_dir: Path
    archive_dir: Path
    template_dir: Path
    ledger_path: Path | None = None
    export_headers: list[str] = field(default_factory=list)
    prefer_existing_headers: bool = False
    tesseract_language: str = "chi_sim+eng"
    use_ocrmypdf: bool = True
    copy_originals: bool = False
    move_originals: bool = True
    export_report_files: bool = False

    @classmethod
    def defaults(cls, root: Path | None = None) -> "AppSettings":
        base = root or Path.home() / "HZ财务归档器"
        return cls(
            output_dir=base,
            archive_dir=base / "archive",
            template_dir=Path(__file__).resolve().parent / "templates",
        )
