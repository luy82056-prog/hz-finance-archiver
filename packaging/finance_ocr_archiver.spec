# Run from the repository root:
#   pyinstaller --clean --noconfirm packaging/finance_ocr_archiver.spec

import os
from pathlib import Path


block_cipher = None
project_root = Path(SPECPATH).resolve().parent
datas = [
    (str(project_root / "finance_ocr_app" / "templates"), "finance_ocr_app/templates"),
    (str(project_root / "finance_ocr_app" / "assets"), "finance_ocr_app/assets"),
]
app_name = "HZ财务归档器"
icon_path = str(project_root / "finance_ocr_app" / "assets" / "app_icon.icns")

a = Analysis(
    [str(project_root / "launcher.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=["yaml", "openpyxl", "pdfplumber", "pytesseract", "PIL", "docx"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=app_name,
)
app = BUNDLE(
    coll,
    name=f"{app_name}.app",
    icon=icon_path,
    bundle_identifier="com.hz.financearchiver",
    info_plist={
        "CFBundleDisplayName": "HZ财务归档器",
        "CFBundleName": "HZ财务归档器",
        "NSHighResolutionCapable": "True",
    },
)
