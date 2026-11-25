from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from .models import AppSettings, ExtractedTable


def extract_text(path: Path, settings: AppSettings) -> tuple[str, Path | None, list[str]]:
    warnings: list[str] = []
    text = ""
    ocr_pdf: Path | None = None
    if path.suffix.lower() == ".docx":
        return _extract_word_text(path, warnings), None, warnings

    if path.suffix.lower() == ".pdf":
        text = _extract_pdf_text(path, warnings)
        if len(text.strip()) >= 40:
            return text, None, warnings
        if settings.use_ocrmypdf and shutil.which("ocrmypdf"):
            ocr_pdf = _run_ocrmypdf(path, settings, warnings)
            if ocr_pdf:
                text = _extract_pdf_text(ocr_pdf, warnings)
        if len(text.strip()) < 40:
            warnings.append("PDF 文字层较少，请确认已安装 Tesseract/OCRmyPDF 或改用人工校正。")
        return text, ocr_pdf, warnings

    text = _extract_image_text(path, settings, warnings)
    return text, None, warnings


def extract_tables(path: Path, text: str = "") -> list[ExtractedTable]:
    if path.suffix.lower() == ".docx":
        tables = _extract_word_tables(path)
        return tables or _table_from_text(text)
    if path.suffix.lower() != ".pdf":
        return _table_from_text(text)
    tables: list[ExtractedTable] = []
    try:
        import pdfplumber

        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    rows = [[_cell_text(cell) for cell in row] for row in table if any(row)]
                    if rows:
                        tables.append(ExtractedTable(rows=rows, source="pdfplumber"))
    except Exception:
        pass
    return tables or _table_from_text(text)


def _extract_pdf_text(path: Path, warnings: list[str]) -> str:
    try:
        import pdfplumber

        pages: list[str] = []
        with pdfplumber.open(str(path)) as pdf:
            for page in pdf.pages:
                pages.append(page.extract_text() or "")
        return "\n".join(pages)
    except Exception as exc:
        warnings.append(f"PDF 文字读取失败：{exc}")
        return ""


def _extract_image_text(path: Path, settings: AppSettings, warnings: list[str]) -> str:
    try:
        import pytesseract
        from PIL import Image

        with Image.open(path) as image:
            return pytesseract.image_to_string(image, lang=settings.tesseract_language)
    except Exception as exc:
        warnings.append(f"图片 OCR 失败：{exc}")
        return ""


def _extract_word_text(path: Path, warnings: list[str]) -> str:
    try:
        from docx import Document

        doc = Document(str(path))
        parts: list[str] = []
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                parts.append(text)
        for table in doc.tables:
            for row in table.rows:
                row_text = "  ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)
        if not parts:
            warnings.append("Word 文档没有读取到正文或表格文字，请确认不是纯图片文档。")
        return "\n".join(parts)
    except Exception as exc:
        warnings.append(f"Word 读取失败：{exc}")
        return ""


def _extract_word_tables(path: Path) -> list[ExtractedTable]:
    try:
        from docx import Document

        doc = Document(str(path))
        tables: list[ExtractedTable] = []
        for table in doc.tables:
            rows: list[list[str]] = []
            for row in table.rows:
                cells = [cell.text.replace("\n", " ").strip() for cell in row.cells]
                if any(cells):
                    rows.append(cells)
            if rows:
                tables.append(ExtractedTable(rows=rows, source="word-table"))
        return tables
    except Exception:
        return []


def _run_ocrmypdf(path: Path, settings: AppSettings, warnings: list[str]) -> Path | None:
    try:
        tmp_dir = Path(tempfile.mkdtemp(prefix="finance_ocr_"))
        output = tmp_dir / f"{path.stem}.ocr.pdf"
        command = [
            "ocrmypdf",
            "--skip-text",
            "--deskew",
            "-l",
            settings.tesseract_language.replace("+", "+"),
            str(path),
            str(output),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=300)
        return output
    except Exception as exc:
        warnings.append(f"OCRmyPDF 处理失败：{exc}")
        return None


def _cell_text(value: object) -> str:
    return "" if value is None else str(value).replace("\n", " ").strip()


def _table_from_text(text: str) -> list[ExtractedTable]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        parts = [part.strip() for part in line.replace("\t", "  ").split("  ") if part.strip()]
        if len(parts) >= 3:
            rows.append(parts)
    return [ExtractedTable(rows=rows, source="text-spacing")] if rows else []
