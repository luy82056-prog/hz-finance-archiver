# 模板维护说明

模板位于 `finance_ocr_app/templates/`，每个 YAML 文件代表一种文档规则。

## 字段

```yaml
name: 增值税发票
document_type: 发票
min_score: 0.15
keywords:
  - 发票
  - 税额
fields:
  party:
    - "销售方名称[:：\\s]*([^\\n]+)"
  date:
    - "(\\d{4}[./-]\\d{1,2}[./-]\\d{1,2})"
  amount:
    - "价税合计[^\\d¥￥-]*[¥￥]?\\s*([\\d,]+\\.\\d{2})"
```

## 支持字段

- `party`：供应商/对方户名/申请人
- `date`：日期
- `document_number`：发票号、流水号、单据号
- `amount`：金额
- `tax_amount`：税额
- `currency`：币种
- `project`：项目名/摘要/用途

## 维护建议

- `keywords` 用来判断文档类型，越稳定越好。
- `fields` 每个字段可以写多个正则，软件会取第一个匹配结果。
- 正则放在 YAML 双引号中时，反斜杠需要写成 `\\`。
- 新增模板后重启软件即可生效。
