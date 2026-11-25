from __future__ import annotations

import re


def enrich_invoice_values(text: str, values: dict[str, str]) -> dict[str, str]:
    values = dict(values)
    values["party"] = _first_nonempty(values.get("party", ""), _seller_name(text))
    values["amount"] = _first_nonempty(_total_amount(text), values.get("amount", ""))
    values["project"] = _first_nonempty(_line_item_project(text), values.get("project", ""))
    values["tax_rate"] = _first_nonempty(values.get("tax_rate", ""), _tax_rate(text))
    values["tax_amount"] = _first_nonempty(values.get("tax_amount", ""), _tax_amount(text))
    return {key: _clean_invoice_value(value) for key, value in values.items()}


def _seller_name(text: str) -> str:
    patterns = [
        r"销\s*名称[:：]\s*([^\n]+)",
        r"销售方[^\n]{0,30}?名称[:：]\s*([^\n]+)",
        r"销售方名称[:：]\s*([^\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _trim_company_field(match.group(1))
    names = re.findall(r"名称[:：]\s*([^\n]+)", text)
    if len(names) >= 2:
        return _trim_company_field(names[1])
    return ""


def _line_item_project(text: str) -> str:
    match = re.search(
        r"项目名称\s+规格型号\s+单\s*位\s+数\s*量\s+单\s*价\s+金\s*额\s+税率/征收率\s+税\s*额\s*\n(?P<body>[\s\S]+?)\n\s*合\s*计",
        text,
    )
    if not match:
        return ""
    parts: list[str] = []
    for raw_line in match.group("body").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"\s+项\s+.*$", "", line)
        line = re.sub(r"\s+(?:个|件|项|次|批|套)\s+.*$", "", line)
        line = re.sub(r"\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?\s+\d+(?:\.\d+)?%.*$", "", line)
        line = line.strip()
        if line and not re.fullmatch(r"[¥￥\d.,%\s]+", line):
            parts.append(line)
    return _normalize_project("".join(parts))


def _tax_rate(text: str) -> str:
    patterns = [
        r"税率/征收率\s+税\s*额\s*\n[\s\S]{0,160}?(\d+(?:\.\d+)?%)",
        r"\s(\d+(?:\.\d+)?%)\s+[¥￥]?\d+(?:\.\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _total_amount(text: str) -> str:
    patterns = [
        r"价税合计\s*[\(（]\s*小写\s*[\)）][^¥￥\d-]*[¥￥]?\s*([+-]?[\d,]+(?:\.\d{2})?)",
        r"[\(（]\s*小写\s*[\)）][^¥￥\d-]*[¥￥]?\s*([+-]?[\d,]+(?:\.\d{2})?)",
        r"价税合计[^¥￥\d-]{0,20}[¥￥]\s*([+-]?[\d,]+(?:\.\d{2})?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _tax_amount(text: str) -> str:
    patterns = [
        r"合\s*计\s*[¥￥]?(?:[\d,]+\.\d{2})\s*[¥￥]?([\d,]+\.\d{2})",
        r"税率/征收率\s+税\s*额\s*\n[\s\S]{0,160}?\d+(?:\.\d+)?%\s+[¥￥]?([\d,]+\.\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _trim_company_field(value: str) -> str:
    value = re.split(r"\s+(?:购|买|销|售|方|信|息)\b", value, maxsplit=1)[0]
    value = re.split(r"\s+统一社会信用代码|\s+纳税人识别号", value, maxsplit=1)[0]
    return value.strip()


def _normalize_project(value: str) -> str:
    value = value.replace("*", " ")
    value = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", value)
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[¥￥]?\d+(?:\.\d+)?\d+(?:\.\d+)?%[¥￥]?\d+(?:\.\d{2})?", "", value)
    value = re.sub(r"[¥￥]?\d+(?:\.\d+)?%[¥￥]?\d+(?:\.\d{2})?", "", value)
    value = re.sub(r"[¥￥]?\d+(?:\.\d{2})$", "", value)
    value = value.replace("信息系统增值服务信息技术服务", "信息系统增值服务 信息技术服务")
    return value.strip()


def _clean_invoice_value(value: str) -> str:
    value = re.sub(r"[\u3000\t]+", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return value.strip(" ：:，,;；\n\r")


def _first_nonempty(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""
