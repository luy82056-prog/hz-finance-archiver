from __future__ import annotations

import sys
from pathlib import Path

try:
    from PySide6.QtCore import QObject, QThread, Qt, Signal
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QProgressBar,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError:
    from PySide2.QtCore import QObject, QThread, Qt, Signal
    from PySide2.QtGui import QIcon, QPixmap
    from PySide2.QtWidgets import (
        QApplication,
        QCheckBox,
        QDialog,
        QDialogButtonBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QLineEdit,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QProgressBar,
        QTableWidget,
        QTableWidgetItem,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

from .exporters import LEDGER_HEADERS
from .exporters import SUPPORTED_EXPORT_HEADERS
from .exporters import normalize_export_headers
from .exporters import read_ledger_headers
from .models import AppSettings, DocumentFields, ProcessResult
from .pipeline import FinancePipeline
from .resources import app_icon_256, app_icon_png
from .utils import iter_supported_files


HEADERS = [
    "文件名",
    "项目名称",
    "金额",
    "文档类型",
    "供应商/对方户名",
    "日期",
    "发票号/流水号",
    "处理状态",
    "归档路径",
]

DEFAULT_PREVIEW_HEADERS = HEADERS


class DropArea(QLabel):
    files_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__("拖入 PDF、图片、Word 或文件夹")
        self.setObjectName("dropArea")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(132)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.toLocalFile()]
        files = iter_supported_files(paths)
        if files:
            self.files_dropped.emit(files)


class Worker(QObject):
    progressed = Signal(int, int, str)
    result_ready = Signal(object)
    finished = Signal(list, object)
    failed = Signal(str)

    def __init__(self, settings: AppSettings, files: list[Path]):
        super().__init__()
        self.settings = settings
        self.files = files

    def run(self) -> None:
        try:
            pipeline = FinancePipeline(self.settings)
            results: list[ProcessResult] = []
            total = len(self.files)
            for index, path in enumerate(self.files, start=1):
                self.progressed.emit(index - 1, total, f"正在处理：{path.name}")
                result = pipeline.process_file(path)
                results.append(result)
                self.result_ready.emit(result)
                self.progressed.emit(index, total, f"已完成：{path.name}")
            exported = pipeline.export_bundle(results)
            self.finished.emit(results, exported)
        except Exception as exc:
            self.failed.emit(str(exc))


class CorrectionDialog(QDialog):
    def __init__(self, fields: DocumentFields, parent=None):
        super().__init__(parent)
        self.setWindowTitle("人工校正")
        self.fields = fields
        self.inputs: dict[str, QLineEdit] = {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        mapping = [
            ("document_type", "文档类型"),
            ("party", "供应商/对方户名"),
            ("date", "日期"),
            ("document_number", "发票号/流水号"),
            ("amount", "金额"),
            ("currency", "币种"),
            ("project", "项目名称"),
            ("notes", "备注"),
        ]
        for attr, label in mapping:
            edit = QLineEdit(str(getattr(fields, attr)))
            self.inputs[attr] = edit
            form.addRow(label, edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def apply(self) -> DocumentFields:
        for attr, edit in self.inputs.items():
            setattr(self.fields, attr, edit.text().strip())
        self.fields.status = "已人工校正"
        self.fields.confidence = max(self.fields.confidence, 0.9)
        return self.fields


class ExportFormatDialog(QDialog):
    def __init__(self, headers: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("编辑导出格式")
        self.resize(520, 420)
        layout = QVBoxLayout(self)
        hint = QLabel("勾选要导出的字段。列表里的字段都已经适配识别和导出。")
        hint.setObjectName("statusLabel")
        self.list_widget = QListWidget()
        selected = set(normalize_export_headers(headers or LEDGER_HEADERS))
        for header in SUPPORTED_EXPORT_HEADERS:
            item = QListWidgetItem(header)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if header in selected else Qt.Unchecked)
            self.list_widget.addItem(item)
        layout.addWidget(hint)
        layout.addWidget(self.list_widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def headers(self) -> list[str]:
        headers: list[str] = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.Checked:
                headers.append(item.text())
        return headers


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("HZ财务归档器")
        self.setWindowIcon(QIcon(str(app_icon_png())))
        self.resize(1220, 780)
        self.settings = AppSettings.defaults()
        self.settings.export_headers = list(LEDGER_HEADERS)
        self.format_edited = False
        self.results: list[ProcessResult] = []
        self.thread: QThread | None = None
        self.worker: Worker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("mainSurface")
        root = QVBoxLayout(central)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 2)
        icon_label = QLabel()
        icon_label.setObjectName("brandIcon")
        pixmap = QPixmap(str(app_icon_256()))
        icon_label.setPixmap(pixmap.scaled(54, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title_box = QVBoxLayout()
        title = QLabel("HZ财务归档器")
        title.setObjectName("brandTitle")
        subtitle = QLabel("本地识别、台账整理、归档打包")
        subtitle.setObjectName("brandSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        root.addWidget(header)

        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.start_processing)
        root.addWidget(self.drop_area)

        controls = QHBoxLayout()
        add_files = QPushButton("添加文件")
        add_files.setObjectName("primaryButton")
        add_files.clicked.connect(self.choose_files)
        add_folder = QPushButton("添加文件夹")
        add_folder.clicked.connect(self.choose_folder)
        choose_ledger = QPushButton("选择 Excel/Word")
        choose_ledger.clicked.connect(self.choose_ledger_file)
        format_button = QPushButton("编辑导出字段")
        format_button.clicked.connect(self.edit_export_format)
        export = QPushButton("导出到台账")
        export.setObjectName("primaryButton")
        export.clicked.connect(self.export_current)
        settings = QPushButton("设置输出目录")
        settings.setText("选择归档文件夹")
        settings.clicked.connect(self.choose_output_dir)
        self.ocrmypdf_check = QCheckBox("优先使用 OCRmyPDF")
        self.ocrmypdf_check.setChecked(True)
        controls.addWidget(add_files)
        controls.addWidget(add_folder)
        controls.addWidget(choose_ledger)
        controls.addWidget(format_button)
        controls.addWidget(export)
        controls.addWidget(settings)
        controls.addWidget(self.ocrmypdf_check)
        controls.addStretch()
        root.addLayout(controls)

        self.progress = QProgressBar()
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.progress)
        root.addWidget(self.status_label)

        self.preview_headers = list(DEFAULT_PREVIEW_HEADERS)
        self.table = QTableWidget(0, len(self.preview_headers))
        self.table.setHorizontalHeaderLabels(self.preview_headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.doubleClicked.connect(self.edit_selected)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        self.log = QTextEdit()
        self.log.setObjectName("logPanel")
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(120)
        root.addWidget(self.log)
        self.setCentralWidget(central)

    def choose_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择财务文档",
            str(Path.home()),
            "Documents (*.pdf *.png *.jpg *.jpeg *.tif *.tiff *.bmp *.docx)",
        )
        self.start_processing([Path(item) for item in files])

    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", str(Path.home()))
        if folder:
            self.start_processing(iter_supported_files([Path(folder)]))

    def choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择归档文件夹", str(self.settings.output_dir))
        if folder:
            self.settings = AppSettings.defaults(Path(folder))
            self.settings.export_headers = self.current_export_headers()
            self.settings.prefer_existing_headers = False
            self.format_edited = True
            self.settings.ledger_path = Path(folder) / "财务台账.xlsx"
            self.log.append(f"归档文件夹已设置为：{Path(folder)}")
            self.log.append(f"Excel 台账将写入：{self.settings.ledger_path}")

    def choose_ledger_file(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "选择或创建 Excel/Word 台账",
            str(self.settings.ledger_path or (self.settings.output_dir / "财务台账.xlsx")),
            "Ledger (*.xlsx *.docx)",
        )
        if path:
            ledger_path = Path(path)
            if ledger_path.suffix.lower() not in {".xlsx", ".docx"}:
                ledger_path = ledger_path.with_suffix(".xlsx")
            self.settings.ledger_path = ledger_path
            self.settings.output_dir = ledger_path.parent
            if ledger_path.exists() and not self.format_edited:
                headers = read_ledger_headers(ledger_path)
                if headers:
                    self.settings.export_headers = normalize_export_headers(headers)
                    self.settings.prefer_existing_headers = True
                    self.preview_headers = list(self.settings.export_headers)
                    self.table.setColumnCount(len(self.preview_headers))
                    self.table.setHorizontalHeaderLabels(self.preview_headers)
                    self.refresh_table()
                    self.log.append("已读取台账第一行作为导出字段。")
            self.log.append(f"台账文件已设置为：{ledger_path}")

    def edit_export_format(self) -> None:
        dialog = ExportFormatDialog(self.current_export_headers(), self)
        if dialog.exec_() == QDialog.Accepted:
            headers = dialog.headers()
            if not headers:
                QMessageBox.information(self, "字段为空", "至少保留一个导出字段。")
                return
            self.settings.export_headers = headers
            self.settings.prefer_existing_headers = False
            self.format_edited = True
            self.preview_headers = headers
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.refresh_table()
            self.log.append("导出字段已更新。")

    def current_export_headers(self) -> list[str]:
        return self.settings.export_headers or list(LEDGER_HEADERS)

    def start_processing(self, files: list[Path]) -> None:
        files = iter_supported_files(files)
        if not files:
            QMessageBox.information(self, "没有文件", "没有找到支持的 PDF、图片或 Word 文件。")
            return
        self.settings.use_ocrmypdf = self.ocrmypdf_check.isChecked()
        self.settings.export_headers = self.current_export_headers()
        self.thread = QThread()
        self.worker = Worker(self.settings, files)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progressed.connect(self.on_progress)
        self.worker.result_ready.connect(self.add_result)
        self.worker.finished.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.progress.setMaximum(len(files))
        self.progress.setValue(0)
        self.log.append(f"开始处理 {len(files)} 个文件")
        self.thread.start()

    def on_progress(self, done: int, total: int, message: str) -> None:
        self.progress.setMaximum(total)
        self.progress.setValue(done)
        self.status_label.setText(message)

    def add_result(self, result: ProcessResult) -> None:
        self.results.append(result)
        self.add_result_row(result)
        if result.errors:
            self.log.append(f"{result.source_path.name}: {'; '.join(result.errors)}")

    def add_result_row(self, result: ProcessResult) -> None:
        fields = result.fields
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = fields.as_ledger_row() if fields else {}
        for col, header in enumerate(self.preview_headers):
            item = QTableWidgetItem(str(values.get(header, "")))
            if header == "处理状态" and values.get(header) in {"需人工复核", "失败"}:
                item.setBackground(Qt.yellow)
            self.table.setItem(row, col, item)

    def refresh_table(self) -> None:
        self.table.setRowCount(0)
        for result in self.results:
            self.add_result_row(result)

    def on_finished(self, results: list[ProcessResult], exported: dict[str, Path]) -> None:
        if exported:
            first_target = next(iter(exported.values()))
            self.status_label.setText(f"完成，已导出到：{first_target}")
            for label, path in exported.items():
                self.log.append(f"{self._export_label(label)}：{path}")
        else:
            self.status_label.setText("完成，当前批次没有可导出的结果")
        for result in results:
            if result.fields and result.fields.archive_path:
                self.log.append(f"原文件已归档：{result.fields.archive_path}")

    def on_failed(self, message: str) -> None:
        QMessageBox.critical(self, "处理失败", message)
        self.status_label.setText("处理失败")

    def export_current(self) -> None:
        if not self.results:
            QMessageBox.information(self, "没有结果", "请先处理文件。")
            return
        self.settings.export_headers = self.current_export_headers()
        self.settings.prefer_existing_headers = False if self.format_edited else self.settings.prefer_existing_headers
        exported = FinancePipeline(self.settings).export_bundle(self.results)
        for label, path in exported.items():
            self.log.append(f"{self._export_label(label)}：{path}")

    def _export_label(self, label: str) -> str:
        return {
            "ledger": "台账写入路径",
            "excel": "Excel 台账",
            "word": "Word 台账",
            "word_summary": "Word 汇总路径",
            "report": "处理报告",
            "failures": "失败列表",
            "zip": "打包文件",
        }.get(label, "导出完成")

    def edit_selected(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self.results):
            return
        result = self.results[row]
        if not result.fields:
            return
        dialog = CorrectionDialog(result.fields, self)
        if dialog.exec_() == QDialog.Accepted:
            fields = dialog.apply()
            values = fields.as_ledger_row()
            for col, header in enumerate(self.preview_headers):
                self.table.setItem(row, col, QTableWidgetItem(str(values.get(header, ""))))
            self.log.append(f"已保存人工校正：{result.source_path.name}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("HZ财务归档器")
    app.setWindowIcon(QIcon(str(app_icon_png())))
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    return app.exec_()


APP_STYLE = """
QWidget#mainSurface {
    background: #f6edd8;
    color: #2f2418;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    font-size: 14px;
}
QFrame#header {
    background: transparent;
}
QLabel#brandIcon {
    padding-right: 8px;
}
QLabel#brandTitle {
    color: #2b2117;
    font-size: 25px;
    font-weight: 700;
    letter-spacing: 0px;
}
QLabel#brandSubtitle {
    color: #6d5b45;
    font-size: 13px;
}
QLabel#dropArea {
    border: 1.5px dashed #b88755;
    border-radius: 8px;
    background: #fff8e9;
    color: #5e4a34;
    font-size: 17px;
    font-weight: 600;
}
QLabel#dropArea:hover {
    background: #fff2d2;
    border-color: #9e6937;
}
QPushButton {
    background: #fbf4e4;
    color: #3d2d1d;
    border: 1px solid #d7bd96;
    border-radius: 6px;
    padding: 8px 13px;
    font-weight: 600;
}
QPushButton:hover {
    background: #f1dfbf;
    border-color: #b88755;
}
QPushButton:pressed {
    background: #e7cfa9;
}
QPushButton#primaryButton {
    background: #8f5d34;
    color: #fff8e9;
    border-color: #744620;
}
QPushButton#primaryButton:hover {
    background: #7f502b;
}
QCheckBox {
    color: #4c3b2b;
    spacing: 8px;
}
QProgressBar {
    background: #fff8e9;
    border: 1px solid #d9c29d;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: #9c6b3d;
    border-radius: 5px;
}
QLabel#statusLabel {
    color: #6d5b45;
    padding-left: 2px;
}
QTableWidget {
    background: #fffaf0;
    alternate-background-color: #f8efd9;
    gridline-color: #e7d4b7;
    border: 1px solid #d9c29d;
    border-radius: 7px;
    selection-background-color: #d8b27c;
    selection-color: #24180f;
}
QHeaderView::section {
    background: #efe0c4;
    color: #3b2a1a;
    border: 0px;
    border-right: 1px solid #d9c29d;
    border-bottom: 1px solid #d9c29d;
    padding: 8px 7px;
    font-weight: 700;
}
QTextEdit#logPanel {
    background: #fff8e9;
    color: #5d4933;
    border: 1px solid #d9c29d;
    border-radius: 7px;
    padding: 7px;
}
QDialog {
    background: #f6edd8;
    color: #2f2418;
}
QLineEdit {
    background: #fffaf0;
    border: 1px solid #d6bd98;
    border-radius: 5px;
    padding: 7px;
    color: #2f2418;
}
"""
