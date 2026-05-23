#!/usr/bin/env python3
"""Render a model-authored AI technical-paper survey into standalone HTML."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render an AI technical-paper survey to standalone HTML.")
    parser.add_argument("markdown_file", help="Model-authored Markdown input.")
    parser.add_argument("html_file", help="HTML output path.")
    parser.add_argument("--manifest", default=None, help="Optional asset_manifest.json path kept for workflow compatibility.")
    parser.add_argument("--title", default=None, help="HTML title.")
    return parser.parse_args()


def load_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    return escaped


def image_html(markdown_line: str, base_dir: Path) -> str | None:
    match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", markdown_line.strip())
    if not match:
        return None
    alt = match.group(1).strip() or "论文附图"
    src = match.group(2).strip()
    path = Path(src)
    if path.is_absolute():
        try:
            src = os.path.relpath(path, base_dir)
        except ValueError:
            src = str(path)
    src = src.replace("\\", "/")
    return (
        '<figure class="paper-figure">'
        f'<img src="{html.escape(src)}" alt="{html.escape(alt)}">'
        f'<figcaption>{html.escape(alt)}</figcaption>'
        "</figure>"
    )


def is_separator(line: str) -> bool:
    cleaned = line.strip().strip("|").replace("|", "").replace(":", "").replace("-", "").strip()
    return cleaned == ""


def slugify(text: str, prefix: str, index: int) -> str:
    ascii_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower()
    return ascii_slug or f"{prefix}-{index}"


def render_table(lines: list[str], start: int) -> tuple[str, int]:
    headers = [cell.strip() for cell in lines[start].strip().strip("|").split("|")]
    rows: list[list[str]] = []
    index = start + 2
    while index < len(lines) and lines[index].strip().startswith("|"):
        rows.append([cell.strip().replace("\\|", "|") for cell in lines[index].strip().strip("|").split("|")])
        index += 1
    parts = ["<div class=\"table-wrap\"><table><thead><tr>"]
    parts.extend(f"<th>{inline_markdown(header)}</th>" for header in headers)
    parts.append("</tr></thead><tbody>")
    for row in rows:
        parts.append("<tr>")
        for value in row[: len(headers)]:
            parts.append(f"<td>{inline_markdown(value)}</td>")
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts), index


def markdown_to_html(markdown: str, base_dir: Path) -> str:
    lines = markdown.splitlines()
    blocks: list[str] = []
    index = 0
    in_list = False
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            index += 1
            continue
        rendered_image = image_html(line, base_dir)
        if rendered_image:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(rendered_image)
        elif line.startswith("|") and index + 1 < len(lines) and lines[index + 1].strip().startswith("|") and is_separator(lines[index + 1]):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            table_html, index = render_table(lines, index)
            blocks.append(table_html)
            continue
        elif line.startswith("# "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h1>{inline_markdown(line[2:].strip())}</h1>")
        elif line.startswith("## "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h2>{inline_markdown(line[3:].strip())}</h2>")
        elif line.startswith("### "):
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<h3>{inline_markdown(line[4:].strip())}</h3>")
        elif line.startswith("- "):
            if not in_list:
                blocks.append("<ul>")
                in_list = True
            blocks.append(f"<li>{inline_markdown(line[2:].strip())}</li>")
        else:
            if in_list:
                blocks.append("</ul>")
                in_list = False
            blocks.append(f"<p>{inline_markdown(line)}</p>")
        index += 1
    if in_list:
        blocks.append("</ul>")
    return "\n".join(blocks)


def overview_with_side_nav(section_html: str) -> str:
    parts = re.split(r"(<h2>.*?</h2>)", section_html, flags=re.S)
    intro = parts[0]
    nav_items: list[str] = []
    sections: list[str] = []
    for raw_index in range(1, len(parts), 2):
        heading = parts[raw_index]
        content = parts[raw_index + 1] if raw_index + 1 < len(parts) else ""
        match = re.search(r"<h2>(.*?)</h2>", heading, flags=re.S)
        title = re.sub(r"<.*?>", "", match.group(1)) if match else f"章节 {len(sections) + 1}"
        title = html.unescape(title)
        section_id = slugify(title, "section", len(sections) + 1)
        heading = re.sub(r"<h2>(.*?)</h2>", f'<h2 id="{section_id}">\\1</h2>', heading, count=1, flags=re.S)
        nav_items.append(f'<a class="side-link" href="#{section_id}">{html.escape(title)}</a>')
        sections.append(f'<section class="report-section">{heading}{content}</section>')
    if not sections:
        return section_html
    return (
        intro
        + '<div class="overview-layout">'
        + '<aside class="side-nav" aria-label="综述章节导航">'
        + "".join(nav_items)
        + "</aside>"
        + '<article class="overview-content">'
        + "".join(sections)
        + "</article></div>"
    )


def top_level_tabs(body: str) -> str:
    parts = re.split(r"(<h1>.*?</h1>)", body, flags=re.S)
    preface = parts[0]
    pages: list[tuple[str, str]] = []
    for index in range(1, len(parts), 2):
        heading = parts[index]
        content = parts[index + 1] if index + 1 < len(parts) else ""
        match = re.search(r"<h1>(.*?)</h1>", heading, flags=re.S)
        title = re.sub(r"<.*?>", "", match.group(1)) if match else f"页面 {len(pages) + 1}"
        title = html.unescape(title)
        page_html = heading + content
        if not pages:
            page_html = overview_with_side_nav(page_html)
            tab_title = "综述"
        else:
            tab_title = title
        pages.append((tab_title, page_html))
    if not pages:
        return body

    buttons: list[str] = []
    panels: list[str] = []
    for index, (title, page_html) in enumerate(pages):
        active = " active" if index == 0 else ""
        selected = "true" if index == 0 else "false"
        hidden = "" if index == 0 else " hidden"
        tab_id = f"top-tab-{index}"
        panel_id = f"top-panel-{index}"
        buttons.append(
            f'<button class="top-tab{active}" id="{tab_id}" role="tab" aria-selected="{selected}" '
            f'aria-controls="{panel_id}" data-top-tab="{panel_id}">{html.escape(title)}</button>'
        )
        panels.append(
            f'<section class="top-panel{active}" id="{panel_id}" role="tabpanel" aria-labelledby="{tab_id}"{hidden}>'
            f"{page_html}</section>"
        )
    return (
        preface
        + '<nav class="top-tabs" role="tablist" aria-label="报告页面">'
        + "".join(buttons)
        + "</nav>"
        + '<div class="top-panels">'
        + "".join(panels)
        + "</div>"
    )


def render_document(body: str, title: str) -> str:
    body = top_level_tabs(body)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --ink:#17202a; --muted:#5d6d7e; --line:#d6dbdf; --accent:#0e6b5c; --bg:#f7f9f9; }}
    body {{ margin:0; font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif; color:var(--ink); background:var(--bg); line-height:1.65; }}
    main {{ max-width:1280px; margin:0 auto; padding:32px 28px 64px; background:#fff; min-height:100vh; }}
    .badge {{ display:inline-block; padding:4px 10px; border:1px solid var(--accent); color:var(--accent); border-radius:999px; font-size:13px; }}
    h1 {{ font-size:30px; line-height:1.2; margin:18px 0 20px; }}
    h2 {{ margin-top:8px; padding-top:8px; font-size:22px; scroll-margin-top:24px; }}
    h3 {{ margin-top:24px; font-size:18px; }}
    p, li {{ font-size:15.5px; }}
    code {{ background:#eef3f2; padding:1px 5px; border-radius:4px; font-family:Consolas,monospace; font-size:0.92em; }}
    .top-tabs {{ display:flex; gap:8px; overflow-x:auto; padding:12px 0 10px; margin:20px 0 12px; border-bottom:1px solid var(--line); position:sticky; top:0; background:#fff; z-index:10; }}
    .top-tab {{ flex:0 0 auto; border:1px solid var(--line); background:#f7f9f9; color:var(--ink); padding:8px 12px; border-radius:6px 6px 0 0; font:inherit; font-size:14px; cursor:pointer; }}
    .top-tab.active {{ background:var(--accent); border-color:var(--accent); color:#fff; }}
    .top-tab:focus-visible {{ outline:2px solid #0b5cad; outline-offset:2px; }}
    .overview-layout {{ display:grid; grid-template-columns:220px minmax(0, 1fr); gap:28px; align-items:start; margin-top:20px; }}
    .side-nav {{ position:sticky; top:70px; display:flex; flex-direction:column; gap:6px; border-right:1px solid var(--line); padding-right:14px; max-height:calc(100vh - 90px); overflow:auto; }}
    .side-link {{ display:block; text-decoration:none; color:var(--ink); border:1px solid var(--line); background:#f7f9f9; padding:8px 10px; border-radius:6px; font-size:14px; }}
    .side-link:hover, .side-link:focus {{ border-color:var(--accent); color:var(--accent); }}
    .report-section {{ border-bottom:1px solid var(--line); padding-bottom:26px; margin-bottom:26px; }}
    .table-wrap {{ overflow-x:auto; margin:14px 0 20px; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; }}
    th, td {{ border:1px solid var(--line); padding:9px 10px; vertical-align:top; }}
    th {{ background:#eef3f2; text-align:left; }}
    .paper-figure {{ margin:16px auto; border:1px solid var(--line); padding:10px; background:#fbfcfc; max-width:760px; }}
    .paper-figure img {{ display:block; max-width:100%; max-height:260px; object-fit:contain; margin:0 auto; }}
    .paper-figure figcaption {{ margin-top:8px; color:var(--muted); font-size:13px; text-align:center; }}
    a {{ color:#0b5cad; }}
    @media (max-width: 760px) {{
      main {{ padding:22px 16px 48px; }}
      .overview-layout {{ display:block; }}
      .side-nav {{ position:static; flex-direction:row; overflow-x:auto; border-right:0; border-bottom:1px solid var(--line); padding:0 0 12px; margin-bottom:18px; }}
      .side-link {{ flex:0 0 auto; }}
    }}
  </style>
</head>
<body>
<main>
  <div class="badge">AI paper survey / local PDF set</div>
  {body}
</main>
<script>
  document.querySelectorAll('.top-tab').forEach((button) => {{
    button.addEventListener('click', () => {{
      document.querySelectorAll('.top-tab').forEach((item) => {{
        item.classList.remove('active');
        item.setAttribute('aria-selected', 'false');
      }});
      document.querySelectorAll('.top-panel').forEach((panel) => {{
        panel.classList.remove('active');
        panel.hidden = true;
      }});
      const panel = document.getElementById(button.dataset.topTab);
      button.classList.add('active');
      button.setAttribute('aria-selected', 'true');
      if (panel) {{
        panel.hidden = false;
        panel.classList.add('active');
      }}
    }});
  }});
</script>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    markdown_path = Path(args.markdown_file).expanduser().resolve()
    html_path = Path(args.html_file).expanduser().resolve()
    load_json(args.manifest)
    title = args.title or "AI技术论文综述报告"
    body = markdown_to_html(markdown_path.read_text(encoding="utf-8"), html_path.parent)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(render_document(body, title), encoding="utf-8")
    print(html_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
