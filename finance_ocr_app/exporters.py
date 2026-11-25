from __future__ import annotations

from copy import copy
from io import BytesIO
import json
import zipfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import ProcessResult
from .utils import ensure_dir


LEDGER_HEADERS = [
    "文件名",
    "项目名称",
    "金额",
    "文档类型",
    "供应商/对方户名",
    "日期",
    "发票号/流水号",
    "归档路径",
    "处理状态",
    "备注",
]

SUPPORTED_EXPORT_HEADERS = [
    "文件名",
    "项目名称",
    "金额",
    "文档类型",
    "供应商/对方户名",
    "日期",
    "发票号/流水号",
    "币种",
    "归档路径",
    "处理状态",
    "备注",
    "识别置信度",
    "税额",
    "税率",
]

EXPORT_HEADER_ALIASES = {
    "项目名": "项目名称",
    "项目": "项目名称",
    "供应商方信息": "供应商/对方户名",
    "对方户名": "供应商/对方户名",
    "发票号": "发票号/流水号",
    "流水号": "发票号/流水号",
    "真实价格": "金额",
    "价税合计": "金额",
    "状态": "处理状态",
}


def export_ledger(
    results: list[ProcessResult],
    output_path: Path,
    headers: list[str] | None = None,
    prefer_existing_headers: bool = False,
) -> Path:
    if output_path.suffix.lower() == ".docx":
        return export_word(results, output_path, headers=headers, prefer_existing_headers=prefer_existing_headers)
    return export_excel(results, output_path, headers=headers, prefer_existing_headers=prefer_existing_headers)


def normalize_export_headers(headers: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for header in headers or LEDGER_HEADERS:
        canonical = EXPORT_HEADER_ALIASES.get(header.strip(), header.strip())
        if canonical in SUPPORTED_EXPORT_HEADERS and canonical not in normalized:
            normalized.append(canonical)
    return normalized or list(LEDGER_HEADERS)


def export_excel(
    results: list[ProcessResult],
    output_path: Path,
    headers: list[str] | None = None,
    prefer_existing_headers: bool = False,
) -> Path:
    ensure_dir(output_path.parent)
    headers = normalize_export_headers(headers)
    if output_path.exists():
        wb = load_workbook(output_path)
        ws = wb["财务台账"] if "财务台账" in wb.sheetnames else wb.active
        existing_headers = _read_headers(ws)
        if existing_headers and prefer_existing_headers:
            headers = normalize_export_headers(existing_headers)
            if existing_headers != headers:
                _replace_headers(ws, headers)
        elif not existing_headers:
            ws.append(headers)
            _style_header(ws)
        elif existing_headers != headers:
            _replace_headers(ws, headers)
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = "财务台账"
        ws.append(headers)
        _style_header(ws)

    template_row = ws.max_row if ws.max_row >= 2 else None
    for result in results:
        row_data = (result.fields.as_ledger_row() if result.fields else {})
        ws.append([row_data.get(header, "") for header in headers])
        if template_row:
            _copy_row_style(ws, template_row, ws.max_row, len(headers))
    _autosize(ws)

    wb.save(output_path)
    return output_path


def export_word(
    results: list[ProcessResult],
    output_path: Path,
    headers: list[str] | None = None,
    prefer_existing_headers: bool = False,
) -> Path:
    from docx import Document

    ensure_dir(output_path.parent)
    headers = normalize_export_headers(headers)
    doc = Document(str(output_path)) if output_path.exists() else Document()
    if doc.tables:
        table = doc.tables[0]
        existing_headers = [cell.text.strip() for cell in table.rows[0].cells]
        if existing_headers and prefer_existing_headers:
            headers = normalize_export_headers(existing_headers)
            if existing_headers != headers:
                table = _replace_word_table_headers(doc, table, headers)
        elif existing_headers != headers:
            table = _replace_word_table_headers(doc, table, headers)
    else:
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        for index, header in enumerate(headers):
            table.rows[0].cells[index].text = header

    for result in results:
        row_data = (result.fields.as_ledger_row() if result.fields else {})
        cells = table.add_row().cells
        for index, header in enumerate(headers[: len(cells)]):
            cells[index].text = str(row_data.get(header, ""))
    doc.save(str(output_path))
    return output_path


def export_word_originals(results: list[ProcessResult], output_path: Path) -> Path:
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.oxml.ns import qn
    from docx.shared import Inches

    ensure_dir(output_path.parent)
    target = Document(str(output_path)) if output_path.exists() else Document()
    has_existing_content = bool(target.paragraphs or target.tables)

    for result in results:
        if has_existing_content:
            target.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        source = Document(str(result.source_path))
        _append_docx_body(source, target, qn, Inches)
        has_existing_content = True

    target.save(str(output_path))
    return output_path


def export_report(results: list[ProcessResult], output_path: Path) -> Path:
    ensure_dir(output_path.parent)
    payload = []
    for result in results:
        payload.append(
            {
                "source_path": str(result.source_path),
                "status": result.fields.status if result.fields else "失败",
                "fields": result.fields.as_ledger_row() if result.fields else {},
                "errors": result.errors,
            }
        )
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def export_failures(results: list[ProcessResult], output_path: Path) -> Path:
    lines = ["文件路径,错误"]
    for result in results:
        if result.errors or (result.fields and result.fields.status in {"失败", "需人工复核"}):
            error_text = "; ".join(result.errors or [result.fields.notes if result.fields else "失败"])
            lines.append(f'"{result.source_path}","{error_text}"')
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def read_ledger_headers(path: Path) -> list[str]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".docx":
        from docx import Document

        doc = Document(str(path))
        if not doc.tables:
            return []
        return [cell.text.strip() for cell in doc.tables[0].rows[0].cells if cell.text.strip()]
    wb = load_workbook(path, read_only=True)
    ws = wb["财务台账"] if "财务台账" in wb.sheetnames else wb.active
    return _read_headers(ws)


def make_zip(output_dir: Path, zip_path: Path) -> Path:
    ensure_dir(zip_path.parent)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in output_dir.rglob("*"):
            if file_path.is_file() and file_path.resolve() != zip_path.resolve():
                archive.write(file_path, file_path.relative_to(output_dir))
    return zip_path


def _style_header(ws) -> None:
    fill = PatternFill("solid", fgColor="E8EEF7")
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center")


def _autosize(ws) -> None:
    for column in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[get_column_letter(column[0].column)].width = min(max(max_len + 2, 10), 42)


def _read_headers(ws) -> list[str]:
    if ws.max_row < 1:
        return []
    return [str(cell.value).strip() for cell in ws[1] if cell.value not in (None, "")]


def _copy_row_style(ws, source_row: int, target_row: int, max_col: int) -> None:
    for col in range(1, max_col + 1):
        source = ws.cell(source_row, col)
        target = ws.cell(target_row, col)
        if source.has_style:
            target._style = copy(source._style)
        if source.number_format:
            target.number_format = source.number_format
        if source.alignment:
            target.alignment = copy(source.alignment)


def _replace_headers(ws, headers: list[str]) -> None:
    if ws.max_column > len(headers):
        ws.delete_cols(len(headers) + 1, ws.max_column - len(headers))
    for index, header in enumerate(headers, start=1):
        ws.cell(1, index).value = header
    _style_header(ws)


def _replace_word_table_headers(doc, table, headers: list[str]):
    rows = [[cell.text for cell in row.cells] for row in table.rows[1:]]
    table_element = table._element
    table_element.getparent().remove(table_element)
    new_table = doc.add_table(rows=1, cols=len(headers))
    new_table.style = "Table Grid"
    for index, header in enumerate(headers):
        new_table.rows[0].cells[index].text = header
    for row_values in rows:
        cells = new_table.add_row().cells
        for index, value in enumerate(row_values[: len(cells)]):
            cells[index].text = value
    return new_table


def _append_docx_body(source, target, qn, inches) -> None:
    for child in source.element.body.iterchildren():
        if child.tag.endswith("}p"):
            source_paragraph = next((p for p in source.paragraphs if p._element is child), None)
            if source_paragraph is not None:
                _append_paragraph(source, source_paragraph, target, qn, inches)
        elif child.tag.endswith("}tbl"):
            source_table = next((t for t in source.tables if t._element is child), None)
            if source_table is not None:
                _append_table(source_table, target)


def _append_paragraph(source, source_paragraph, target, qn, inches) -> None:
    paragraph = target.add_paragraph()
    try:
        paragraph.style = source_paragraph.style.name
    except Exception:
        pass
    paragraph.alignment = source_paragraph.alignment
    for run in source_paragraph.runs:
        if run.text:
            new_run = paragraph.add_run(run.text)
            _copy_run_style(run, new_run)
        for blip in run._element.xpath(".//a:blip"):
            rel_id = blip.get(qn("r:embed")) or blip.get(qn("r:link"))
            if not rel_id or rel_id not in source.part.rels:
                continue
            image_part = source.part.rels[rel_id].target_part
            try:
                paragraph.add_run().add_picture(BytesIO(image_part.blob), width=inches(4.8))
            except Exception:
                pass


def _append_table(source_table, target) -> None:
    row_count = len(source_table.rows)
    col_count = max((len(row.cells) for row in source_table.rows), default=0)
    if not row_count or not col_count:
        return
    table = target.add_table(rows=row_count, cols=col_count)
    table.style = "Table Grid"
    for row_index, row in enumerate(source_table.rows):
        for col_index, cell in enumerate(row.cells[:col_count]):
            table.cell(row_index, col_index).text = cell.text


def _copy_run_style(source_run, target_run) -> None:
    target_run.bold = source_run.bold
    target_run.italic = source_run.italic
    target_run.underline = source_run.underline
    if source_run.font.size:
        target_run.font.size = source_run.font.size
    if source_run.font.name:
        target_run.font.name = source_run.font.name
