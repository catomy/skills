#!/usr/bin/env python3
"""Validate the generated AI paper survey report against the skill contract."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


REQUIRED_PAPER_SECTIONS = ["背景与定位", "问题与挑战", "解决方案", "关键图表", "下一步计划"]
PLACEHOLDER_MARKERS = [
    "用不少于",
    "这些只是阅读线索",
    "写作要求",
    "可从提取图片中挑选",
    "指定目录中没有可分析",
]
GENERIC_FIGURE_CAPTIONS = {"论文附图", "架构图", "流程图", "方案图"}
EMPTY_TABLE_ROW_RE = re.compile(r"(?m)^\|\s*(?:\|\s*)+$")
MARKDOWN_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


class ImageSourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "img":
            return
        attributes = dict(attrs)
        self.sources.append(attributes.get("src") or "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a rendered paper_series_report.html and its Markdown source.")
    parser.add_argument("markdown_file", help="Final report Markdown.")
    parser.add_argument("html_file", help="Rendered HTML report.")
    parser.add_argument("--manifest", required=True, help="asset_manifest.json from extraction.")
    parser.add_argument("--min-cjk-per-paper", type=int, default=800, help="Minimum Chinese characters per paper page.")
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))


def split_h1_pages(markdown: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^#\s+(.+?)\s*$", markdown))
    pages: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        pages.append((match.group(1).strip(), markdown[start:end]))
    return pages


def cjk_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def resolve_markdown_image(path_text: str, base_dir: Path) -> Path:
    image_path = Path(path_text.strip())
    if image_path.is_absolute():
        return image_path
    return (base_dir / image_path).resolve()


def validate_markdown_images(markdown: str, markdown_dir: Path) -> list[str]:
    errors: list[str] = []
    for index, match in enumerate(MARKDOWN_IMAGE_RE.finditer(markdown), start=1):
        alt_text = match.group(1).strip()
        image_target = match.group(2).strip()
        if not image_target:
            errors.append(f"Markdown image {index} has an empty path.")
            continue
        if image_target.startswith(("http://", "https://", "data:")):
            continue
        resolved = resolve_markdown_image(image_target, markdown_dir)
        if not resolved.exists():
            errors.append(f"Markdown image {index} does not exist: {image_target}")
        if alt_text in GENERIC_FIGURE_CAPTIONS:
            errors.append(f"Markdown image {index} caption is too generic; use the original caption translation.")
    return errors


def validate_html_images(html: str) -> list[str]:
    errors: list[str] = []
    parser = ImageSourceParser()
    parser.feed(html)
    for index, source in enumerate(parser.sources, start=1):
        if not source.strip():
            errors.append(f"HTML image {index} has an empty src attribute.")
    return errors


def validate(markdown: str, html: str, manifest: dict[str, Any], min_cjk_per_paper: int, markdown_dir: Path) -> list[str]:
    errors: list[str] = []
    documents = manifest.get("documents") or []
    pages = split_h1_pages(markdown)

    if not pages:
        errors.append("Markdown has no top-level # pages.")
        return errors

    expected_pages = len(documents) + 1
    if len(pages) != expected_pages:
        errors.append(f"Expected {expected_pages} top-level Markdown pages (overview + papers), found {len(pages)}.")

    tab_count = len(re.findall(r'<button class="top-tab\b', html))
    if tab_count != expected_pages:
        errors.append(f"Expected {expected_pages} top tabs in HTML, found {tab_count}.")

    if "综述" not in pages[0][0] and "综述" not in html[:5000]:
        errors.append("First page does not appear to be the overview tab.")

    if len(re.findall(r'<a class="side-link"', html)) < 3 and documents:
        errors.append("Overview side navigation has too few sections.")

    for token in ["text:", "table:", "image:"]:
        if token in html:
            errors.append(f"Internal evidence token leaked into HTML: {token}")

    for marker in PLACEHOLDER_MARKERS:
        if marker in markdown or marker in html:
            errors.append(f"Starter placeholder appears in final report: {marker}")

    if EMPTY_TABLE_ROW_RE.search(markdown):
        errors.append("Starter table row appears in final Markdown; fill or remove empty table rows.")

    errors.extend(validate_markdown_images(markdown, markdown_dir))
    errors.extend(validate_html_images(html))

    paper_pages = pages[1:]
    for index, ((title, page), document) in enumerate(zip(paper_pages, documents, strict=False), start=1):
        count = cjk_count(page)
        if count < min_cjk_per_paper:
            errors.append(f"Paper page {index} has {count} Chinese characters, below {min_cjk_per_paper}: {title}")
        for section in REQUIRED_PAPER_SECTIONS:
            if f"### {section}" not in page:
                errors.append(f"Paper page {index} missing section: {section}")
        doc_title = str(document.get("title") or document.get("file_name") or "")
        if doc_title and doc_title not in title and title not in doc_title:
            errors.append(f"Paper page {index} title may not match scanned PDF: page='{title}', manifest='{doc_title}'")

    figures = re.findall(r'<figure class="paper-figure">.*?</figure>', html, flags=re.S)
    for figure_index, figure in enumerate(figures, start=1):
        caption_match = re.search(r"<figcaption>(.*?)</figcaption>", figure, flags=re.S)
        caption = re.sub(r"<.*?>", "", caption_match.group(1)).strip() if caption_match else ""
        if not caption:
            errors.append(f"Figure {figure_index} has no caption.")
        if any(token in caption for token in ["text:", "table:", "image:"]):
            errors.append(f"Figure {figure_index} caption contains an internal evidence token.")
        if caption in GENERIC_FIGURE_CAPTIONS:
            errors.append(f"Figure {figure_index} caption is too generic; use the original caption translation.")

    return errors


def main() -> int:
    args = parse_args()
    markdown_path = Path(args.markdown_file).expanduser().resolve()
    markdown = markdown_path.read_text(encoding="utf-8")
    html = Path(args.html_file).expanduser().resolve().read_text(encoding="utf-8")
    manifest = load_json(args.manifest)
    errors = validate(markdown, html, manifest, args.min_cjk_per_paper, markdown_path.parent)
    if errors:
        print("Report validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Report validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
