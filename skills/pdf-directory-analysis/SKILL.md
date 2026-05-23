---
name: pdf-directory-analysis
description: "Run this skill whenever the user wants to analyze a folder of AI research PDFs, model technical reports, arXiv papers, benchmark papers, architecture papers, multimodal or agent papers, alignment/safety papers, or Chinese prompts such as 分析论文目录, 批量阅读PDF论文, 生成技术综述, 模型报告解读, or 做文献综述网页. It extracts local evidence from the PDF directory, builds detailed per-paper reading notes, synthesizes a survey-style overview, and produces a standalone HTML report with an overview tab followed by one tab per scanned paper."
---

# PDF Directory Analysis

## Purpose

Run this skill when the user wants a directory of AI technical-paper PDFs analyzed as a survey. After the skill runs, the output should include a standalone HTML review report.

The workflow is intentionally narrow: scan the requested PDF directory, extract local evidence, build one detailed page for every scanned paper, synthesize a survey-style overview, render `paper_series_report.html`, and validate that the HTML matches the report contract.

The skill must stay generic. Do not bind the analysis to any specific paper, model family, company, benchmark, topic, or number of files unless that information appears in the user's PDFs.

Do not add outside research, alternate file formats, or alternate report modes unless the user explicitly asks for them.

## Main Workflow

1. Confirm the source PDF directory and output directory. If no output directory is specified, use `<source-directory>/pdf-analysis-output/skill-run-YYYYMMDD-HHMMSS`. For quick reruns, `pdf-analysis-output/skill-run-latest` is acceptable when the user clearly wants to overwrite the latest local result.
2. Install extraction dependencies if needed:

```bash
python -m pip install -r skills/pdf-directory-analysis/requirements.txt
```

3. Extract local PDF evidence:

```bash
python skills/pdf-directory-analysis/scripts/extract_pdf_assets.py <pdf-directory> --out-dir <output-directory> --recursive
```

Use `--recursive` only when the user wants subfolders included.

4. Build detailed per-paper pages before writing the overview. Do this for every PDF found in the requested directory; do not assume the directory contains one, two, or any fixed number of files. Each paper page should focus on:

- background and context;
- problem and challenges;
- proposed solution;
- important figures or visual aids, when available;
- next-step plan, including reading, reproduction, research, and engineering follow-up.

Use evidence IDs internally to navigate extracted assets, but do not expose evidence IDs in the final HTML.

For each paper, first identify the original structure from the extracted headings and full text, such as abstract, introduction, background, method, architecture, training, inference, experiments, results, discussion, limitation, and conclusion. The final paper page should simplify that original structure instead of inventing an unrelated structure. Keep the required paper-tab sections as the reader-facing organization, but write each section from the paper's own order and emphasis.

Each paper page should be substantive, not a short card. As a default quality bar, write at least 800 Chinese characters per paper page unless the PDF extraction is too weak to support it.

Only attach figures when they directly explain architecture, method flow, training/inference pipeline, system design, or key experimental setup. Do not attach simple logos, covers, decorative images, author blocks, or unrelated screenshots. Every retained figure should be introduced and interpreted in nearby text.

Every retained figure must use a faithful Chinese translation of the original paper caption or legend. Do not invent a new caption, do not shorten it into a generic title, and do not use the image filename as the caption. If the extractor did not capture a caption, review the PDF directly; if the caption still cannot be recovered, state that the original caption was not extractable instead of guessing.

5. Create the Markdown working draft:

```bash
python skills/pdf-directory-analysis/scripts/create_report_starter.py <output-directory>/asset_manifest.json <output-directory>/paper_series_report.md
```

6. Replace the starter placeholders with the final report. Do not leave instructional placeholder text in `paper_series_report.md`.

Write in this order:

- First, write every paper page as a structured reading note. Use the paper's original heading flow as the backbone, then simplify it into `背景与定位`, `问题与挑战`, `解决方案`, `关键图表`, and `下一步计划`.
- Second, write the overview page as a survey synthesis. The overview should compare the papers, identify technical routes, extract shared views and disagreements, and describe development trends.
- Third, revise the whole Markdown so the reader can quickly understand the technology and identify what to read, reproduce, or investigate next.

Do not include strings such as `text:...`, `table:...`, or `image:...` in the final report unless the user explicitly asks for traceability details.

7. Render the HTML produced by this skill run. The renderer creates a top-level tab layout: first tab is `综述`, and each remaining tab is one scanned paper. Inside the overview tab, `##` sections are shown as a left-side navigation.

```bash
python skills/pdf-directory-analysis/scripts/render_html_report.py <output-directory>/paper_series_report.md <output-directory>/paper_series_report.html --manifest <output-directory>/asset_manifest.json --title "AI技术论文综述报告"
```

8. Validate the generated report:

```bash
python skills/pdf-directory-analysis/scripts/validate_report.py <output-directory>/paper_series_report.md <output-directory>/paper_series_report.html --manifest <output-directory>/asset_manifest.json
```

If validation fails, fix `paper_series_report.md`, render again, and rerun validation. Do not return the report as finished until validation passes or until you clearly explain the remaining blocker.

9. Return the path to `paper_series_report.html`. Mention extraction gaps, weak OCR, missing tables/images, skipped files, or validation caveats only when they affect confidence.

## Regression Evals

Use `evals/evals.json` when changing this skill. The eval set covers the main risk areas: multi-paper synthesis, single-paper report generation, weak extraction or missing captions, and non-AI PDF near-misses.

For each eval, compare the generated output against the expected behavior and run `scripts/validate_report.py` whenever a Markdown/HTML report is produced. Prefer adding a new eval before changing behavior that affects report structure, figure handling, or triggering scope.

## Proven Run Pattern

Use this pattern from the successful test run:

1. Extract assets and inspect `asset_manifest.json` before writing.
2. For each PDF, inspect title, headings, abstract, section excerpts, tables, image list, and any extracted figure captions.
3. Draft the paper tabs first. Each tab should be a real reading note, not a short evidence inventory.
4. Only after the paper tabs are clear, write the overview as a literature-review synthesis.
5. Use figures sparingly. If a figure has no original caption candidate and cannot be verified from the PDF, skip it rather than inventing a caption.
6. Render HTML and run validation. Check top tabs, overview side navigation, per-paper character count, required sections, figure captions, and absence of internal evidence IDs.

## Outputs From A Skill Run

Primary output:

- `paper_series_report.html`: standalone survey-style HTML report. The first tab is the overview. Remaining tabs are generated dynamically from scanned papers.

Traceability artifacts:

- `paper_series_report.md`: intermediate working draft used to render the HTML.
- `asset_manifest.json`: deterministic extraction manifest and internal grounding IDs.
- `analysis_packet.md`: compact evidence packet for writing the report.
- `extracted_text/`: one text file per PDF.
- `tables/`: extracted table CSV files grouped by PDF.
- `images/`: extracted images grouped by PDF.
- `text_index.csv`, `tables_index.csv`, `images_index.csv`: traceability indexes.

Quality-control artifact:

- Validation command output from `scripts/validate_report.py`.

## Report Layout

The final HTML should use this interaction model:

- Top tab 1: `综述`, containing survey-level synthesis.
- Top tabs 2..N: one tab per scanned paper.
- Inside `综述`, the left side shows navigation for overview sections.
- Inside each paper tab, content is organized for fast technical understanding.

Overview sections:

- `## 综述摘要`: topic, paper set, and 3-5 main takeaways.
- `## 研究背景与问题脉络`: why this line of work matters and how the problem is evolving.
- `## 方法谱系`: group papers by method family, architecture route, training strategy, evaluation style, or system design.
- `## 关键观点与共识`: what the papers broadly agree on and why.
- `## 分歧与争议`: where the papers differ, what assumptions drive the differences, and what remains uncertain.
- `## 技术演进路线`: the development path across papers.
- `## 发展趋势与开放问题`: likely next steps, bottlenecks, and unsolved questions.
- `## 读者建议`: reading order, reproduction focus, and practical takeaways.
- `## 综述边界`: extraction quality, coverage limits, and uncertainty.

Paper tab sections:

- `### 背景与定位`
- `### 问题与挑战`
- `### 解决方案`
- `### 关键图表`
- `### 下一步计划`

Each paper tab should be structured and detailed. `背景与定位`, `问题与挑战`, and `解决方案` are the core sections; `关键图表` is optional and should only include figures that support nearby explanation. Within those reader-facing sections, follow the paper's original structure in simplified form rather than writing a generic template.

## AI Technical Paper Lens

Adapt the review to whatever AI domain the PDFs cover. Common lenses include model architecture, training recipe, data strategy, inference efficiency, evaluation design, multimodal pipeline, agent workflow, deployment constraints, safety, reliability, open problems, and future directions.

Only use lenses that are actually relevant to the provided PDFs.

## Grounding Rules

- Use only evidence extracted from the specified PDF directory unless the user explicitly requests outside research.
- Use local evidence IDs internally to find and verify claims, such as `text:Paper_ID`, `table:Paper_ID:p003:t01`, or `image:Paper_ID:p004:i02`.
- Do not show those evidence IDs in the final HTML. Convert them into readable reasoning such as “the architecture discussion indicates...” or “the evaluation section suggests...”.
- The final HTML uses one paper tab per scanned PDF and does not hard-code the number of paper tabs.
- Preserve the paper's own structure as the basis for each per-paper reading note, simplified for fast understanding.
- Use original figure captions/legends as the source for figure captions in the HTML, translated faithfully into Chinese.
- Treat keyword counts and headings as retrieval signals, not conclusions.
- Separate direct PDF evidence from synthesis or inference in wording, but keep the final report readable.
- If extraction is weak, say so plainly and recommend OCR before over-interpreting the document.

## Validation Rules

Before completing a run, ensure:

- HTML top tabs equal one overview tab plus one tab per scanned PDF.
- The overview has side navigation from `##` sections.
- Every paper tab contains the five required `###` sections.
- Every paper tab normally has at least 800 Chinese characters.
- The final Markdown and HTML contain no starter instructions or internal evidence IDs.
- Every retained figure has a meaningful caption translated from the original paper caption or legend.
- Every Markdown image path resolves from the output directory, and every rendered HTML image `src` is non-empty.
- Starter table rows such as `|  |  |` are removed from the final report.
- Simple images, covers, logos, author blocks, and unrelated screenshots are excluded.

## Resources

- `scripts/extract_pdf_assets.py`: extracts text, tables, images, indexes, and internal grounding IDs.
- `scripts/create_report_starter.py`: creates the Markdown working draft.
- `scripts/render_html_report.py`: renders `paper_series_report.html` after the review draft is written.
- `scripts/validate_report.py`: validates the final Markdown and HTML against the skill contract.
- `references/report-schema.md`: report structure and review checklist.
- `references/html_report_template.md`: optional writing scaffold for the working draft.
