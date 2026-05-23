# HTML Report Template

Use this structure when writing the Markdown working draft that will be rendered to `paper_series_report.html`.

Rules:

- Write like a survey or literature review.
- Use only local evidence from the requested PDF directory unless the user asks for outside research.
- Do not show evidence IDs in the final HTML.
- Do not make the report a table/image/evidence listing.
- Do not leave starter instructions or checklist text in the final Markdown.
- Explain conclusions and reasons in natural language.
- Mark trends and recommendations as synthesis when they go beyond direct paper claims.
- The first top-level tab is the overview page.
- Remaining top-level tabs are paper pages generated from scanned PDFs.
- The overview page uses left-side navigation for `##` sections.
- Write the paper pages first, then write the overview from the completed paper notes.

Overview page:

- `# AI技术论文综述报告`
- `## 综述摘要`
- `## 研究背景与问题脉络`
- `## 方法谱系`
- `## 关键观点与共识`
- `## 分歧与争议`
- `## 技术演进路线`
- `## 发展趋势与开放问题`
- `## 读者建议`
- `## 综述边界`

Paper page:

- `# [paper title]`
- `### 背景与定位`
- `### 问题与挑战`
- `### 解决方案`
- `### 关键图表`
- `### 下一步计划`

Paper page requirements:

- Write at least 800 Chinese characters per paper page when extraction quality allows.
- Use structured paragraphs or tables, not a few short bullets.
- First identify the paper's original section flow, then simplify it into the paper page. Keep the reader-facing section names, but do not invent a structure unrelated to the original paper.
- Attach figures only when they directly support the explanation of architecture, method flow, system design, or key experimental setup.
- Do not attach logos, covers, decorative images, author blocks, or simple images that do not help explain the technology.
- Explain every retained figure in nearby text.
- Use a faithful Chinese translation of the original figure caption or legend for every retained figure. If the caption cannot be extracted, review the PDF; if still unavailable, state that the original caption was not extractable instead of inventing one.

Before returning the HTML, run:

```bash
python skills/pdf-directory-analysis/scripts/validate_report.py <output-directory>/paper_series_report.md <output-directory>/paper_series_report.html --manifest <output-directory>/asset_manifest.json
```

Revise and rerender until the validator passes, unless extraction quality makes that impossible.
