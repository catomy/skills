#!/usr/bin/env python3
"""Deterministically extract PDF text, tables, images, and grounding indexes."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import site
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "our",
    "that",
    "the",
    "this",
    "to",
    "via",
    "we",
    "with",
    "within",
    "using",
    "model",
    "models",
    "paper",
    "report",
    "figure",
    "table",
    "section",
    "page",
    "arxiv",
    "https",
    "http",
}


SECTION_PATTERNS = {
    "abstract": r"\babstract\b",
    "introduction": r"\bintroduction\b",
    "method": r"\b(method|methodology|architecture|approach)\b",
    "experiments": r"\b(experiment|evaluation|benchmark|result)s?\b",
    "conclusion": r"\bconclusion[s]?\b",
}


THEME_KEYWORDS = {
    "architecture": ["architecture", "moe", "mixture", "expert", "dense", "hybrid", "attention", "transformer"],
    "reasoning_efficiency": ["thinking", "reasoning", "inference", "latency", "efficient", "budget", "compute"],
    "multimodal": ["omni", "multimodal", "omnimodal", "audio", "visual", "video", "speech", "vision"],
    "training_data": ["training", "dataset", "data", "pre-training", "post-training", "reinforcement", "tokens"],
    "evaluation": ["benchmark", "evaluation", "performance", "sota", "surpass", "achieves", "results"],
    "language": ["multilingual", "language", "languages", "dialects", "cross-lingual"],
    "availability": ["open", "apache", "release", "publicly", "accessible", "api", "github"],
}


@dataclass
class TableAsset:
    id: str
    document: str
    page: int
    index: int
    rows: int
    columns: int
    path: str
    preview: list[list[str]]


@dataclass
class ImageAsset:
    id: str
    document: str
    page: int
    index: int
    width: int
    height: int
    ext: str
    path: str
    caption: str = ""
    caption_source: str = ""


@dataclass
class DocumentPacket:
    doc_id: str
    file_name: str
    relative_path: str
    absolute_path: str
    title: str
    date_hint: str
    pages: int
    word_count: int
    extraction_status: str
    extraction_method: str
    text_path: str
    grounding_refs: dict[str, str]
    abstract_excerpt: str
    section_excerpts: dict[str, str]
    headings: list[str]
    top_terms: list[str]
    theme_keyword_counts: dict[str, int]
    tables: list[TableAsset] = field(default_factory=list)
    images: list[ImageAsset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract deterministic PDF evidence assets from a directory.")
    parser.add_argument("pdf_directory", help="Directory containing PDF files.")
    parser.add_argument("--out-dir", default=None, help="Output directory.")
    parser.add_argument("--recursive", action="store_true", help="Include PDF files in subdirectories.")
    parser.add_argument("--dependency-dir", default=None, help="Optional project-local Python package directory.")
    parser.add_argument("--max-images-per-pdf", type=int, default=120, help="Maximum saved images per PDF.")
    parser.add_argument("--min-image-area", type=int, default=4096, help="Skip tiny images below this pixel area.")
    parser.add_argument("--table-preview-rows", type=int, default=5, help="Rows saved in table previews.")
    parser.add_argument("--section-excerpt-chars", type=int, default=2400, help="Characters to save per section excerpt.")
    return parser.parse_args()


def configure_dependency_paths(source: Path, dependency_dir: str | None) -> None:
    candidates = []
    if dependency_dir:
        candidates.append(Path(dependency_dir).expanduser().resolve())
    candidates.extend([source / ".python-packages", Path.cwd() / ".python-packages"])
    for candidate in candidates:
        if candidate.exists():
            site.addsitedir(str(candidate))


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def safe_stem(path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", path.stem).strip("._")
    return stem or "document"


def list_pdfs(root: Path, recursive: bool) -> list[Path]:
    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted([path for path in root.glob(pattern) if path.is_file()], key=lambda item: str(item).lower())


def text_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def word_count(text: str) -> int:
    english = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-']*", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    return len(english) + len(cjk)


def top_terms(text: str, limit: int = 20) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text.lower())
    filtered = [word.strip("-") for word in words if word not in STOPWORDS and len(word.strip("-")) >= 3]
    return [word for word, _ in Counter(filtered).most_common(limit)]


def infer_title(path: Path, text: str, metadata: dict[str, str]) -> str:
    title = (metadata.get("title") or "").strip()
    if title and title.lower() not in {"untitled", "none", "null"}:
        return title
    for line in text_lines(text)[:50]:
        if re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}$", line):
            continue
        if line.lower().startswith(("http://", "https://", "arxiv:", "abstract")):
            continue
        if 6 <= len(line) <= 160 and not re.search(r"\.{4,}|/{2,}|\\", line):
            return line
    return path.stem


def infer_date(text: str) -> str:
    for line in text_lines(text)[:80]:
        match = re.search(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\b", line)
        if match:
            return match.group(1).replace("/", "-")
    match = re.search(r"\b(20\d{2})\b", text[:3000])
    return match.group(1) if match else ""


def detect_headings(text: str, limit: int = 28) -> list[str]:
    headings: list[str] = []
    seen: set[str] = set()
    for line in text_lines(text)[:4500]:
        clean = re.sub(r"\s+", " ", line).strip()
        if not 3 <= len(clean) <= 140:
            continue
        looks_like_heading = bool(
            re.match(r"^\d+(\.\d+)*\s+[A-Z][A-Za-z0-9 ,:;\-/()]+$", clean)
            or re.match(
                r"^(abstract|introduction|background|method|methodology|architecture|experiments?|evaluation|results?|discussion|conclusion|references)\b",
                clean,
                re.I,
            )
            or (clean.isupper() and len(clean.split()) <= 10)
        )
        if looks_like_heading and clean.lower() not in seen:
            seen.add(clean.lower())
            headings.append(clean)
        if len(headings) >= limit:
            break
    return headings


def section_excerpt(text: str, pattern: str, max_chars: int) -> str:
    match = re.search(pattern, text, flags=re.I)
    if not match:
        return ""
    return clean_text(text[match.start() : match.start() + max_chars])


def section_excerpts(text: str, max_chars: int) -> dict[str, str]:
    return {name: section_excerpt(text, pattern, max_chars) for name, pattern in SECTION_PATTERNS.items()}


def abstract_excerpt(text: str, max_chars: int = 1600) -> str:
    extracted = section_excerpt(text, SECTION_PATTERNS["abstract"], max_chars)
    if extracted:
        return extracted
    return clean_text("\n".join(text_lines(text)[:24]))[:max_chars]


def keyword_counts(text: str) -> dict[str, int]:
    lowered = text.lower()
    counts: dict[str, int] = {}
    for theme, keywords in THEME_KEYWORDS.items():
        counts[theme] = sum(len(re.findall(rf"\b{re.escape(keyword.lower())}\b", lowered)) for keyword in keywords)
    return counts


def normalize_table(table: list[list[Any]]) -> list[list[str]]:
    max_cols = max((len(row) for row in table if row), default=0)
    rows: list[list[str]] = []
    for row in table:
        values = ["" if cell is None else re.sub(r"\s+", " ", str(cell)).strip() for cell in row]
        rows.append(values + [""] * (max_cols - len(values)))
    return rows


def looks_like_section_boundary(line: str) -> bool:
    clean = re.sub(r"\s+", " ", line).strip()
    if not clean:
        return True
    if clean.startswith(("•", "-", "–", "—")):
        return True
    if re.match(r"^(table|figure|fig\.?)\s+\d+", clean, flags=re.I):
        return True
    if re.match(
        r"^(\d+(\.\d+)*)\s+(abstract|introduction|background|method|methodology|architecture|experiments?|evaluation|results?|discussion|conclusion|references)\b",
        clean,
        flags=re.I,
    ):
        return True
    if re.match(
        r"^(abstract|introduction|background|method|methodology|architecture|experiments?|evaluation|results?|discussion|conclusion|references)\b",
        clean,
        flags=re.I,
    ):
        return True
    return False


def extract_figure_captions(page_text: str, max_chars: int = 1400) -> list[str]:
    """Extract likely figure captions from page text without interpreting them."""
    raw_lines = [re.sub(r"\s+", " ", line).strip() for line in page_text.splitlines()]
    captions: list[str] = []
    index = 0
    start_pattern = re.compile(r"^(figure|fig\.?)\s+\d+[A-Za-z0-9.\-]*\s*[:.\-|]?\s+.+", flags=re.I)
    while index < len(raw_lines):
        line = raw_lines[index]
        if not start_pattern.match(line):
            index += 1
            continue
        parts = [line]
        index += 1
        continuation_count = 0
        while index < len(raw_lines) and continuation_count < 8:
            next_line = raw_lines[index]
            if not next_line:
                break
            if start_pattern.match(next_line) or looks_like_section_boundary(next_line):
                break
            parts.append(next_line)
            continuation_count += 1
            if len(" ".join(parts)) >= max_chars:
                break
            index += 1
        caption = clean_text(" ".join(parts))[:max_chars]
        if caption and caption not in captions:
            captions.append(caption)
        continue
    return captions


def extract_figure_captions_from_blocks(page: Any) -> list[str]:
    captions: list[str] = []
    try:
        blocks = sorted(page.get_text("blocks") or [], key=lambda block: (block[1], block[0]))
    except Exception:  # noqa: BLE001
        return extract_figure_captions(page.get_text("text") or "")
    for block in blocks:
        if len(block) < 5:
            continue
        block_text = str(block[4] or "")
        for caption in extract_figure_captions(block_text, max_chars=900):
            if caption not in captions:
                captions.append(caption)
    return captions


def extract_tables(path: Path, document_id: str, document_title: str, table_dir: Path, preview_rows: int) -> list[TableAsset]:
    import pdfplumber  # type: ignore

    table_dir.mkdir(parents=True, exist_ok=True)
    assets: list[TableAsset] = []
    with pdfplumber.open(str(path)) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            for table_number, table in enumerate(page.extract_tables() or [], start=1):
                normalized = normalize_table(table)
                if not normalized or len(normalized) < 2:
                    continue
                csv_path = table_dir / f"page_{page_number:03d}_table_{table_number:02d}.csv"
                with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
                    csv.writer(handle).writerows(normalized)
                assets.append(
                    TableAsset(
                        id=f"table:{document_id}:p{page_number:03d}:t{table_number:02d}",
                        document=document_title,
                        page=page_number,
                        index=table_number,
                        rows=len(normalized),
                        columns=max(len(row) for row in normalized),
                        path=str(csv_path),
                        preview=normalized[:preview_rows],
                    )
                )
    return assets


def extract_text_and_images(
    path: Path,
    document_id: str,
    text_path: Path,
    image_dir: Path,
    max_images: int,
    min_image_area: int,
) -> tuple[str, int, dict[str, str], list[ImageAsset], list[str]]:
    import fitz  # type: ignore

    warnings: list[str] = []
    image_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(path))
    text_parts = [page.get_text("text") or "" for page in doc]
    metadata = {str(k).lower(): str(v).strip() for k, v in (doc.metadata or {}).items() if v}
    images: list[ImageAsset] = []
    seen: set[int] = set()

    for page_number, page in enumerate(doc, start=1):
        page_captions = extract_figure_captions_from_blocks(page)
        if not page_captions:
            page_captions = extract_figure_captions(text_parts[page_number - 1] if page_number - 1 < len(text_parts) else "")
        for image_number, image in enumerate(page.get_images(full=True), start=1):
            xref = int(image[0])
            if xref in seen:
                continue
            seen.add(xref)
            extracted = doc.extract_image(xref)
            width = int(extracted.get("width") or 0)
            height = int(extracted.get("height") or 0)
            if width * height < min_image_area:
                continue
            ext = str(extracted.get("ext") or "bin")
            image_path = image_dir / f"page_{page_number:03d}_image_{image_number:02d}.{ext}"
            image_path.write_bytes(extracted["image"])
            caption_index = min(image_number - 1, len(page_captions) - 1)
            caption = page_captions[caption_index] if caption_index >= 0 else ""
            images.append(
                ImageAsset(
                    id=f"image:{document_id}:p{page_number:03d}:i{image_number:02d}",
                    document="",
                    page=page_number,
                    index=image_number,
                    width=width,
                    height=height,
                    ext=ext,
                    path=str(image_path),
                    caption=caption,
                    caption_source="same-page figure-caption heuristic" if caption else "",
                )
            )
            if len(images) >= max_images:
                warnings.append(f"Image extraction stopped at max_images_per_pdf={max_images}.")
                break
        if len(images) >= max_images:
            break

    text = clean_text("\n\n".join(text_parts))
    text_path.write_text(text, encoding="utf-8")
    return text, len(doc), metadata, images, warnings


def analyze_pdf(path: Path, root: Path, out_dir: Path, args: argparse.Namespace) -> DocumentPacket:
    document_id = safe_stem(path)
    text_dir = out_dir / "extracted_text"
    table_dir = out_dir / "tables" / document_id
    image_dir = out_dir / "images" / document_id
    text_dir.mkdir(parents=True, exist_ok=True)
    text_path = text_dir / f"{document_id}.txt"
    warnings: list[str] = []

    try:
        text, pages, metadata, images, image_warnings = extract_text_and_images(
            path, document_id, text_path, image_dir, args.max_images_per_pdf, args.min_image_area
        )
        warnings.extend(image_warnings)
        extraction_method = "pymupdf"
    except Exception as exc:  # noqa: BLE001
        text = ""
        pages = 0
        metadata = {}
        images = []
        extraction_method = "failed"
        warnings.append(f"Text/image extraction failed: {exc}")

    title = infer_title(path, text, metadata)
    for image in images:
        image.document = title

    try:
        tables = extract_tables(path, document_id, title, table_dir, args.table_preview_rows)
    except Exception as exc:  # noqa: BLE001
        tables = []
        warnings.append(f"Table extraction failed: {exc}")

    status = "ok" if word_count(text) >= 80 else "weak"
    if status == "weak":
        warnings.append("Text extraction is weak; OCR may be required for scanned PDFs.")

    return DocumentPacket(
        doc_id=document_id,
        file_name=path.name,
        relative_path=str(path.relative_to(root)),
        absolute_path=str(path.resolve()),
        title=title,
        date_hint=infer_date(text),
        pages=pages,
        word_count=word_count(text),
        extraction_status=status,
        extraction_method=extraction_method,
        text_path=str(text_path),
        grounding_refs={
            "text": f"text:{document_id}",
            "abstract": f"text:{document_id}#section:abstract",
            **{name: f"text:{document_id}#section:{name}" for name in SECTION_PATTERNS},
        },
        abstract_excerpt=abstract_excerpt(text),
        section_excerpts=section_excerpts(text, args.section_excerpt_chars),
        headings=detect_headings(text),
        top_terms=top_terms(text),
        theme_keyword_counts=keyword_counts(text),
        tables=tables,
        images=images,
        warnings=warnings,
    )


def write_indexes(documents: list[DocumentPacket], out_dir: Path) -> None:
    with (out_dir / "text_index.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "document",
                "relative_path",
                "title",
                "date_hint",
                "pages",
                "word_count",
                "extraction_status",
                "text_path",
            ],
        )
        writer.writeheader()
        for doc in documents:
            writer.writerow(
                {
                    "id": f"text:{doc.doc_id}",
                    "document": doc.file_name,
                    "relative_path": doc.relative_path,
                    "title": doc.title,
                    "date_hint": doc.date_hint,
                    "pages": doc.pages,
                    "word_count": doc.word_count,
                    "extraction_status": doc.extraction_status,
                    "text_path": doc.text_path,
                }
            )

    with (out_dir / "tables_index.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "document", "page", "index", "rows", "columns", "path"])
        writer.writeheader()
        for doc in documents:
            for table in doc.tables:
                writer.writerow(
                    {
                        "id": table.id,
                        "document": table.document,
                        "page": table.page,
                        "index": table.index,
                        "rows": table.rows,
                        "columns": table.columns,
                        "path": table.path,
                    }
                )

    with (out_dir / "images_index.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["id", "document", "page", "index", "width", "height", "ext", "path", "caption", "caption_source"],
        )
        writer.writeheader()
        for doc in documents:
            for image in doc.images:
                writer.writerow(
                    {
                        "id": image.id,
                        "document": image.document,
                        "page": image.page,
                        "index": image.index,
                        "width": image.width,
                        "height": image.height,
                        "ext": image.ext,
                        "path": image.path,
                        "caption": image.caption,
                        "caption_source": image.caption_source,
                    }
                )


def build_packet_markdown(documents: list[DocumentPacket], source: Path) -> str:
    lines = [
        "# PDF Evidence Packet",
        "",
        f"- Generated: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"- Source directory: `{source}`",
        f"- PDF count: {len(documents)}",
        f"- Table count: {sum(len(doc.tables) for doc in documents)}",
        f"- Image count: {sum(len(doc.images) for doc in documents)}",
        "",
        "## Extraction Index",
        "",
        "| Evidence ID | Document | Pages | Words | Tables | Images | Status | Text Path |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for doc in documents:
        lines.append(
            f"| text:{doc.doc_id} | {doc.title} | {doc.pages} | {doc.word_count} | {len(doc.tables)} | {len(doc.images)} | {doc.extraction_status} | `{doc.text_path}` |"
        )

    lines.extend(
        [
            "",
            "## Model Analysis Task",
            "",
            "Use `asset_manifest.json`, `extracted_text/`, `tables/`, and `images/` as the evidence base. Keyword counts are signals only, not final conclusions.",
            "First complete per-paper analysis, then synthesize the series-level report.",
            "Do not reproduce the evidence inventory as the main report. Use evidence IDs internally for verification, but omit text/table/image IDs from the final HTML and explain reasons in natural language.",
            "",
            "1. Analyze each paper's research problem, method, architecture or process, experiments, results, contribution, and limitations.",
            "2. Compare papers across goals, methods, data, metrics, conclusions, technical routes, and use cases.",
            "3. Summarize the technical route and evolution across the paper series.",
            "4. Identify key questions and challenges. Each question should explain why it matters without exposing internal evidence IDs in the final HTML.",
            "5. Generate actionable implications. Separate direct evidence, model inference, and uncertainty.",
            "",
            "## Per-Document Evidence Summary",
            "",
        ]
    )
    for doc in documents:
        lines.extend(
            [
                f"### {doc.title}",
                "",
                f"- File: `{doc.relative_path}`",
                f"- Evidence IDs: text:{doc.doc_id}; abstract: text:{doc.doc_id}#section:abstract",
                f"- Date hint: {doc.date_hint or 'unknown'}",
                f"- Top-term signals: {', '.join(doc.top_terms[:12])}",
                f"- Asset counts: {len(doc.tables)} tables; {len(doc.images)} images",
                "",
                "**Abstract Excerpt**",
                "",
                doc.abstract_excerpt,
                "",
            ]
        )
        if doc.tables:
            lines.extend(["**Table Evidence IDs**", ""])
            lines.extend([f"- {table.id}: page {table.page}, {table.rows} rows x {table.columns} columns, `{table.path}`" for table in doc.tables])
            lines.append("")
        if doc.images:
            lines.extend(["**Image Evidence IDs and Caption Candidates**", ""])
            for image in doc.images:
                caption = f" Caption candidate: {image.caption}" if image.caption else " Caption candidate: not extracted; review the PDF before inventing one."
                lines.append(f"- {image.id}: page {image.page}, {image.width}x{image.height}, `{image.path}`.{caption}")
            lines.append("")
        if doc.headings:
            lines.extend(["**Heading Signals**", ""])
            lines.extend([f"- {heading}" for heading in doc.headings[:18]])
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    source = Path(args.pdf_directory).expanduser().resolve()
    if not source.exists() or not source.is_dir():
        print(f"Source directory does not exist: {source}")
        return 2
    configure_dependency_paths(source, args.dependency_dir)

    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else source / "pdf-analysis-output"
    out_dir.mkdir(parents=True, exist_ok=True)

    documents = [analyze_pdf(path, source, out_dir, args) for path in list_pdfs(source, args.recursive)]
    write_indexes(documents, out_dir)

    payload = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "source_directory": str(source),
        "documents": [asdict(document) for document in documents],
        "analysis_policy": {
            "script_role": "deterministic extraction only",
            "model_role": "generic AI technical-paper interpretation, comparison, technical-route synthesis, challenges, and actionable implications",
            "report_scope": "Use only local evidence extracted from the requested PDF directory unless the user explicitly asks for outside research. Use evidence IDs internally, but do not expose them in the final HTML.",
            "final_output": "Render the model-authored Markdown as paper_series_report.html.",
        },
    }
    manifest_path = out_dir / "asset_manifest.json"
    packet_path = out_dir / "analysis_packet.md"
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    packet_path.write_text(build_packet_markdown(documents, source), encoding="utf-8")

    print(f"PDFs processed: {len(documents)}")
    print(f"Tables extracted: {sum(len(doc.tables) for doc in documents)}")
    print(f"Images saved: {sum(len(doc.images) for doc in documents)}")
    print(f"Manifest: {manifest_path}")
    print(f"Analysis packet: {packet_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
