from __future__ import annotations

from .models import DocumentFields
from .invoice_rules import enrich_invoice_values
from .templates import ExtractionTemplate, choose_template


def classify_and_extract(filename: str, text: str, templates: list[ExtractionTemplate]) -> DocumentFields:
    template = choose_template(text, templates)
    if template is None:
        return DocumentFields(
            filename=filename,
            status="需人工复核",
            confidence=0.0,
            notes="未匹配到模板",
        )

    values, confidence = template.extract(text)
    if template.document_type == "发票":
        values = enrich_invoice_values(text, values)
    fields = DocumentFields(
        filename=filename,
        document_type=template.document_type,
        confidence=confidence,
        status="已识别" if confidence >= 0.45 else "需人工复核",
    )
    for key, value in values.items():
        if hasattr(fields, key):
            setattr(fields, key, value)
    if not fields.currency:
        fields.currency = "CNY"
    if confidence < 0.45:
        fields.notes = "置信度较低，请人工校正"
    return fields
