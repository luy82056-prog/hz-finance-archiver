# HZ 财务归档器

把财务文档识别、规则提取、台账追加、Word 汇总与文件归档组织到本地工具中。

## 快速开始

建议使用 Python 3.11 和虚拟环境，并安装 Tesseract 与所需 OCR 语言包：

```sh
python -m venv .venv
# 先按下面的平台命令激活 .venv，再继续
python -m pip install -r requirements.txt
python -m finance_ocr_app
```

执行后两条命令前激活虚拟环境。在 macOS/Linux 用 `source .venv/bin/activate`，Windows PowerShell 用 `.venv\Scripts\Activate.ps1`。批处理帮助可运行 `python -m finance_ocr_app.cli --help`。Windows 打包见 [构建说明](README_WINDOWS.md)。

## 使用示例

先用一份虚构凭证的副本验证。选择输入文件及输出目录，检查类型和字段提取结果，确认后再尝试归档与台账更新。正式归档会移动输入文件。可用 [用户指南](docs/USER_GUIDE.md) 和 [模板指南](docs/TEMPLATE_GUIDE.md) 查看不同文件的流程。

## 代码结构

- `finance_ocr_app/` 包含界面、OCR、识别规则、文档导出与归档。
- `finance_ocr_app/templates/` 包含可调整的凭证分类规则。
- `packaging/` 包含 Windows 安装配置及 PyInstaller 规格。

## 开发过程

[查看开发历程](DEVELOPMENT.md)

## 许可与使用范围

项目源码采用 MIT。以虚构或获授权的文件测试。OCR 引擎和系统组件各自遵循原许可。
