from __future__ import annotations

import argparse
from pathlib import Path

from .models import AppSettings
from .pipeline import FinancePipeline
from .utils import iter_supported_files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="本地财务 OCR 归档批处理")
    parser.add_argument("inputs", nargs="+", help="输入文件或文件夹")
    parser.add_argument("--output", default=None, help="输出目录")
    parser.add_argument("--no-ocrmypdf", action="store_true", help="禁用 OCRmyPDF")
    parser.add_argument("--lang", default="chi_sim+eng", help="Tesseract 语言，例如 chi_sim+eng")
    args = parser.parse_args(argv)

    root = Path(args.output).expanduser().resolve() if args.output else None
    settings = AppSettings.defaults(root)
    settings.use_ocrmypdf = not args.no_ocrmypdf
    settings.tesseract_language = args.lang

    files = iter_supported_files([Path(item).expanduser().resolve() for item in args.inputs])
    if not files:
        print("没有找到支持的 PDF/图片/Word 文件。")
        return 2

    pipeline = FinancePipeline(settings)

    def progress(done: int, total: int, message: str) -> None:
        print(f"[{done}/{total}] {message}")

    results = pipeline.process_files(files, progress=progress)
    exported = pipeline.export_bundle(results)
    print("导出完成：")
    for name, path in exported.items():
        print(f"- {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
