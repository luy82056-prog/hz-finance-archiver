from __future__ import annotations

import shutil
from pathlib import Path

from .classifier import classify_and_extract
from .exporters import export_failures, export_ledger, export_report, export_word_originals, make_zip
from .extractors import extract_tables, extract_text
from .models import IMAGE_EXTENSIONS, WORD_EXTENSIONS, AppSettings, DocumentFields, ProcessResult
from .templates import load_templates
from .utils import copy_file_unique, ensure_dir, normalize_date_for_path, safe_name, unique_path


class FinancePipeline:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        ensure_dir(settings.output_dir)
        self.templates = load_templates(settings.template_dir)

    def process_file(self, path: Path) -> ProcessResult:
        result = ProcessResult(source_path=path)
        try:
            text, working_path, warnings = extract_text(path, self.settings)
            result.text = text
            result.working_path = working_path
            result.errors.extend(warnings)
            result.tables = extract_tables(working_path or path, text)
            if path.suffix.lower() in WORD_EXTENSIONS:
                result.fields = DocumentFields(
                    filename=path.name,
                    document_type="Word原文",
                    project=self._extract_word_project(text),
                    confidence=1.0,
                    status="已汇总",
                )
            else:
                result.fields = classify_and_extract(path.name, text, self.templates)
            self._archive(result)
        except Exception as exc:
            result.errors.append(str(exc))
        finally:
            if result.fields is None:
                result.fields = DocumentFields(filename=path.name, status="失败", notes="; ".join(result.errors))
        return result

    def process_files(self, paths: list[Path], progress=None) -> list[ProcessResult]:
        results: list[ProcessResult] = []
        total = len(paths)
        for index, path in enumerate(paths, start=1):
            if progress:
                progress(index - 1, total, f"正在处理：{path.name}")
            results.append(self.process_file(path))
            if progress:
                progress(index, total, f"已完成：{path.name}")
        return results

    def export_bundle(self, results: list[ProcessResult]) -> dict[str, Path]:
        output_dir = ensure_dir(self.settings.output_dir)
        exported: dict[str, Path] = {}
        word_results = [result for result in results if result.source_path.suffix.lower() in WORD_EXTENSIONS]
        ledger_results = [result for result in results if result.source_path.suffix.lower() not in WORD_EXTENSIONS]

        if ledger_results:
            ledger_path = self.settings.ledger_path or output_dir / "财务台账.xlsx"
            ledger = export_ledger(
                ledger_results,
                ledger_path,
                headers=self.settings.export_headers,
                prefer_existing_headers=self.settings.prefer_existing_headers,
            )
            exported["ledger"] = ledger
            if ledger.suffix.lower() == ".xlsx":
                exported["excel"] = ledger
            if ledger.suffix.lower() == ".docx":
                exported["word"] = ledger

        if word_results:
            word_summary = export_word_originals(
                word_results,
                output_dir / "Word汇总归档.docx",
            )
            exported["word_summary"] = word_summary

        if self.settings.export_report_files:
            report_path = export_report(results, output_dir / "处理报告.json")
            failures_path = export_failures(results, output_dir / "失败与复核列表.csv")
            zip_path = make_zip(output_dir, output_dir / "财务归档包.zip")
            exported.update({"report": report_path, "failures": failures_path, "zip": zip_path})
        return exported

    def _archive(self, result: ProcessResult) -> None:
        if not result.fields:
            return
        suffix = result.source_path.suffix.lower()
        if self.settings.move_originals and (suffix == ".pdf" or suffix in IMAGE_EXTENSIONS):
            self._move_original(result)
            return
        if not self.settings.copy_originals:
            result.fields.archive_path = ""
            return
        year, month = normalize_date_for_path(result.fields.date)
        doc_type = safe_name(result.fields.document_type, "未知")
        party = safe_name(result.fields.party, "未知主体")
        archive_dir = self.settings.archive_dir / year / month / doc_type / party
        archived_original = copy_file_unique(result.source_path, archive_dir)
        if result.working_path and result.working_path.exists():
            target = archive_dir / f"{result.source_path.stem}.ocr.pdf"
            shutil.copy2(result.working_path, target)
        result.fields.archive_path = str(archived_original)

    def _move_original(self, result: ProcessResult) -> None:
        if not result.fields:
            return
        try:
            output_dir = ensure_dir(self.settings.output_dir)
            suffix = result.source_path.suffix.lower()
            project = safe_name(result.fields.project, "未知项目")
            amount = safe_name(result.fields.amount, "未知金额")
            target = unique_path(output_dir / f"{project} {amount}{suffix}")
            if result.source_path.resolve() == target.resolve():
                result.fields.archive_path = str(target)
                return
            moved = Path(shutil.move(str(result.source_path), str(target)))
            result.fields.archive_path = str(moved)
        except Exception as exc:
            result.errors.append(f"原文件移动失败：{exc}")

    def _extract_word_project(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if "项目" not in stripped:
                continue
            if "：" in stripped:
                return stripped.split("：", 1)[1].strip()
            if ":" in stripped:
                return stripped.split(":", 1)[1].strip()
            return stripped
        return ""
