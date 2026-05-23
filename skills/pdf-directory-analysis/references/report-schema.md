# Report Schema

Use this reference when reviewing or customizing the AI technical-paper directory survey output.

## Primary Output From A Skill Run

- `paper_series_report.html`: standalone survey-style HTML report produced after the skill is run.
- The first top-level tab is the overview page.
- Each remaining top-level tab is one scanned paper.
- The overview page has left-side navigation for its second-level sections.
- The report should pass `scripts/validate_report.py` before being returned as finished.
- When the skill behavior changes, review `evals/evals.json` and add a new eval for any newly supported report shape or failure mode.

## Working and Traceability Files

- `paper_series_report.md`: intermediate model-authored source used to render the HTML.
- `asset_manifest.json`: canonical extraction manifest and internal grounding IDs.
- `analysis_packet.md`: compact handoff for model analysis.
- `text_index.csv`: text extraction index.
- `extracted_text/`: full extracted text, one `.txt` per PDF.
- `tables/<pdf-name>/`: extracted table CSV files.
- `images/<pdf-name>/`: extracted image files.
- `tables_index.csv`: table asset index.
- `images_index.csv`: image asset index.
- Validation output from `scripts/validate_report.py`: final quality gate for tab count, required sections, per-paper length, captions, and internal evidence leakage.

## Markdown Structure

- The first `#` section is the overview page.
- Every later `#` section is a paper page.
- Overview sections use `##` headings.
- Paper page sections use `###` headings.
- Write paper pages first, then write the overview from the completed paper notes.

## Overview Sections

- Survey abstract.
- Research background and problem context.
- Method taxonomy.
- Key viewpoints and consensus.
- Disagreements and controversies.
- Technical evolution path.
- Trends and open problems.
- Reader recommendations.
- Survey boundary.

## Paper Page Sections

Each scanned PDF should have one paper page with:

- Background and positioning.
- Problems and challenges.
- Proposed solution.
- Key figures or visual aids.
- Next-step plan.

Each paper page should normally contain at least 800 Chinese characters. It should be structured enough for a reader to quickly understand the technical background, the core problem, why the problem is hard, what solution is proposed, why the solution might work, limitations, and what to do next.

Before writing each paper page, identify the paper's original structure from headings and full text. Simplify that structure into the reader-facing sections above. Do not invent an unrelated outline or force all papers into the same internal order when their original sections differ.

Figures are optional. Include only architecture diagrams, method-flow diagrams, training/inference pipelines, system diagrams, or key experimental setup diagrams that are directly discussed in nearby text. Exclude logos, covers, decorative images, author blocks, or simple images that do not help explain the technology.

Every retained figure must use a faithful Chinese translation of the original figure caption or legend. Do not invent a title, abbreviate the caption into a generic summary, or use filenames as captions. If the caption cannot be extracted automatically, inspect the PDF manually; if it still cannot be recovered, say the original caption was not extractable.

## Final HTML Rules

- Do not show local evidence IDs such as `text:...`, `table:...`, or `image:...` in the final HTML.
- Do not turn extracted tables, images, or indexes into the main content.
- Do not leave starter instructions such as “用不少于...” or “写作要求...” in the final report.
- Do not leave starter table rows such as `|  |  |` in the final report.
- Every Markdown image path should resolve from the output directory, and every rendered HTML image `src` should be non-empty.
- Explain reasons in natural language.
- Organize papers by problem, solution, technical route, trend, and follow-up plan.
- Mark inferred trends as synthesis rather than direct paper conclusions.
- Run the validator after rendering; if it fails, revise the Markdown and render again.

## Review Checklist

1. Confirm every PDF in the requested directory appears in `asset_manifest.json`.
2. Confirm the number of paper tabs matches the PDFs scanned; do not assume a fixed count.
3. Confirm the first tab is the overview page.
4. Confirm the overview page has side navigation for `##` sections.
5. Confirm each paper page focuses on background, problems/challenges, solution, figures, and next-step plan.
6. Confirm each paper page is substantive, normally at least 800 Chinese characters unless extraction quality prevents it.
7. Confirm every retained figure is directly tied to nearby explanatory text.
8. Confirm retained figure captions are faithful Chinese translations of original captions or legends.
9. Confirm simple/decorative images are excluded.
10. Confirm per-paper notes preserve each paper's original structure in simplified form.
11. Confirm no internal evidence IDs appear in the final HTML.
12. Confirm no starter placeholder text appears in the final Markdown or HTML.
13. Confirm no empty starter table rows remain.
14. Confirm all retained image paths resolve.
15. Run `scripts/validate_report.py` and confirm it passes.
16. Confirm the user-facing output from the skill run is `paper_series_report.html`.
