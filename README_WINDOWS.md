# HZ财务归档器 Windows 安装包说明

最终交付给普通 Windows 用户的文件应该是：

```text
HZ财务归档器-Windows安装包.exe
```

用户双击这个安装包即可出现安装向导，不需要打开 PowerShell。

当前制作环境是 macOS，不能直接生成可验证的 Windows 原生安装包。请使用下面任一方式在 Windows 环境中生成最终安装包。

## 推荐方式：GitHub Actions 自动生成

项目已内置 GitHub Actions 工作流：

```text
.github\workflows\build-windows-installer.yml
```

上传到 GitHub 后，在 `Actions` 中手动运行 `Build Windows Installer`，完成后下载 Artifact：

```text
HZ财务归档器-Windows安装包.exe
```

## 本地 Windows 电脑生成

1. 安装 Python 3.10 或更高版本，并勾选 `Add python.exe to PATH`。
2. 安装 Inno Setup 6：https://jrsoftware.org/isdl.php
3. 先把整个 zip 解压到桌面，不要在压缩包窗口里直接双击。
4. 双击 `Build-Windows-Setup.cmd`。
5. 如果失败，窗口不会立即消失，完整日志在 `build_installer.log`。
6. 生成结果在：

```text
installer_output\HZ财务归档器-Windows安装包.exe
```

## 当前功能

- 批量拖入 PDF、图片、Word 或文件夹。
- PDF/图片生成 `财务台账.xlsx`。
- PDF/图片原文件移动到归档文件夹，并按 `项目名称 金额` 自动改名。
- Word 原文汇总到 `Word汇总归档.docx`，保留正文、简单表格和图片。
- 导出字段使用勾选列表，避免无效自定义字段。

## 扫描件 OCR

数字 PDF 可以直接读取文字层。扫描 PDF 或图片 OCR 需要额外安装：

- Tesseract OCR for Windows
- 中文语言包 `chi_sim`
- 可选：OCRmyPDF、Ghostscript、Poppler

未安装 OCR 工具时，软件仍可处理已有文字层的 PDF，并支持人工校正。

## 文件说明

- `Build-Windows-Setup.cmd`：在 Windows 上生成最终安装包，推荐双击这个
- `03_生成Windows安装包.bat`：中文入口，会转到 `Build-Windows-Setup.cmd`
- `build_installer.log`：生成失败时查看这个日志
- `.github\workflows\build-windows-installer.yml`：GitHub Actions 自动生成 Windows 安装包
- `packaging\finance_ocr_archiver_windows.spec`：PyInstaller Windows 打包配置
- `packaging\hz_finance_archiver.iss`：Inno Setup 安装包配置
- `finance_ocr_app\assets\app_icon.ico`：Windows 图标
