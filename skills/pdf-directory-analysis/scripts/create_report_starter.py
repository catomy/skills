#!/usr/bin/env python3
"""Create a Markdown starter for a survey-style AI paper HTML report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create starter Markdown for a survey-style AI paper HTML report.")
    parser.add_argument("manifest", help="Path to asset_manifest.json.")
    parser.add_argument("output_markdown", help="Starter Markdown output path.")
    return parser.parse_args()


def load_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))


def build_overview(documents: list[dict[str, Any]]) -> list[str]:
    return [
        "# AI技术论文综述报告",
        "",
        "## 综述摘要",
        "",
        "- 本次扫描到的论文共同围绕什么主题展开？",
        "- 这个主题为什么重要？",
        "- 最重要的 3-5 个结论是什么？",
        "",
        "## 研究背景与问题脉络",
        "",
        "- 用自然语言解释这组论文所在的问题背景。",
        "- 说明这些论文共同回应了什么技术瓶颈、产品需求或研究争议。",
        "- 交代问题如何从早期形态演变到当前形态。",
        "",
        "## 方法谱系",
        "",
        "| 方法/路线 | 代表论文 | 解决的问题 | 核心做法 | 优势 | 局限 |",
        "|---|---|---|---|---|---|",
        "|  |  |  |  |  |  |",
        "",
        "## 关键观点与共识",
        "",
        "- 共识 1：这些论文共同认可什么判断？为什么？",
        "- 共识 2：它们在方法或评测上形成了什么共同方向？为什么？",
        "- 共识 3：它们对未来系统形态暗示了什么？为什么？",
        "",
        "## 分歧与争议",
        "",
        "| 分歧点 | 不同选择 | 背后的假设 | 影响 |",
        "|---|---|---|---|",
        "|  |  |  |  |",
        "",
        "## 技术演进路线",
        "",
        "- 阶段 1：早期问题或基础能力是什么？",
        "- 阶段 2：中间出现了哪些关键方法变化？",
        "- 阶段 3：当前论文把路线推进到了哪里？",
        "- 路线背后的主要驱动力是什么：数据、算力、架构、评测、产品需求，还是安全可靠性？",
        "",
        "## 发展趋势与开放问题",
        "",
        "- 趋势 1：根据这些论文，下一步最可能发展的方向是什么？为什么？",
        "- 趋势 2：哪些瓶颈会继续限制这条路线？为什么？",
        "- 开放问题：哪些问题还没有被这些论文解决？",
        "",
        "## 读者建议",
        "",
        "- 阅读顺序：先读哪篇，再读哪篇，原因是什么？",
        "- 复现重点：哪些实验、数据、指标或系统细节最值得复核？",
        "- 研究启发：如果继续做这个方向，下一步应该验证什么？",
        "- 工程启发：如果要落地，最需要提前评估什么风险和成本？",
        "",
        "## 综述边界",
        "",
        f"- 本综述基于本次扫描到的 {len(documents)} 篇 PDF。",
        "- 若用于正式研究，需要补充更多相关论文、复现结果和第三方评测。",
        "- 趋势判断和读者建议属于综合分析，不等同于论文作者的直接结论。",
        "",
    ]


def build_paper_pages(documents: list[dict[str, Any]], output_dir: Path) -> list[str]:
    lines: list[str] = []
    if not documents:
        return ["# 未扫描到论文", "", "指定目录中没有可分析的 PDF 文件。", ""]
    for index, document in enumerate(documents, start=1):
        title = document.get("title", "") or document.get("file_name", "") or f"论文 {index}"
        pages = document.get("pages", 0)
        words = document.get("word_count", 0)
        status = document.get("extraction_status", "")
        terms = ", ".join((document.get("top_terms") or [])[:8]) or "暂无明显主题词"
        headings = document.get("headings") or []
        heading_signal = "；".join(str(item) for item in headings[:10]) or "未自动识别到稳定章节标题，请直接阅读正文并按原文结构梳理。"
        images = document.get("images") or []
        lines.extend(
            [
                f"# {index}. {title}",
                "",
        "### 背景与定位",
        "",
        f"- 基本信息：约 {pages} 页，提取文本约 {words} 词，提取状态：{status}。",
        f"- 主题线索：{terms}。这些只是阅读线索，不要直接当作结论。",
        f"- 原文结构线索：{heading_signal}",
        "- 按原论文的 Abstract / Introduction / Background 等开头部分简化，不要脱离论文自造背景。用不少于 180 字说明它处在什么研究背景下、和同目录其他论文是什么关系，以及它试图推进哪条技术路线或解决哪类真实需求。",
        "",
        "### 问题与挑战",
        "",
        "- 按原文的问题陈述、动机、局限讨论和实验铺垫来简化。用不少于 200 字说明这篇论文最核心的问题是什么，为什么难，涉及数据、模型、训练、推理、评测、系统、成本、安全或产品体验中的哪些挑战。",
        "- 单独指出论文没有解决或只部分解决的问题。",
        "",
        "### 解决方案",
        "",
        "- 按原论文 Method / Architecture / Training / Inference / Experiments 等章节顺序压缩，不要完全改成自己的结构。",
        "- 用不少于 300 字说明论文提出的核心方案。",
        "- 结构化拆解关键模块、算法、架构、训练流程、推理机制、数据策略或评测设计。",
        "- 解释方案为什么可能有效，它相对已有路线的主要变化是什么。",
        "- 说明局限、适用条件和失败风险。",
        "",
        "### 关键图表",
        "",
            ]
        )
        lines.append("- 只有当图片能解释架构、方案流程、训练流程、推理流程、系统模块或关键实验设计时才插入。不要插入 logo、封面装饰、作者信息、简单图标或与文字无直接关系的图片。")
        lines.append("- 如果插入图片，先用一段文字说明它和“解决方案”或“问题挑战”的关系，再插入 Markdown 图片，并在图后解释读者应该看什么。")
        lines.append("- 图注必须来自原论文 figure caption / legend 的忠实中文翻译，不要自行概括、缩短或改标题；如果自动提取不到图注，写明“原文图注未能自动提取，需要回 PDF 复核”，不要编造。")
        if images:
            captioned = [image for image in images if image.get("caption")]
            lines.append(f"- 已提取 {len(images)} 张候选图片，其中 {len(captioned)} 张带有同页图注候选。只保留和文字分析直接相关的架构图、流程图、系统图、方案图或关键实验设计图。")
        else:
            lines.append("- 未提取到可用图片。若论文包含关键结构图或结果图，请回到 PDF 人工查看并补充解释。")
        lines.extend(
            [
                "",
                "### 下一步计划",
                "",
                "- 用不少于 160 字给出下一步计划。",
                "- 阅读下一步：还应该补读哪些相关章节、论文或背景材料？",
                "- 复现下一步：最值得复核的数据、实验、指标、消融或系统细节是什么？",
                "- 研究下一步：基于这篇论文，可以继续追问哪些问题？",
                "- 工程下一步：如果要落地，最先要评估哪些成本、风险和依赖条件？",
                "",
                "> 写作要求：本论文页总字数不少于 800 字。内容必须以原文结构为骨架进行简化，先讲清背景、问题挑战和解决方案，再决定是否附图。图像必须和相邻文字直接相关，图注必须忠实翻译原文。",
                "",
            ]
        )
    return lines


def build_starter(manifest: dict[str, Any], output_markdown: Path) -> str:
    documents = manifest.get("documents") or []
    lines: list[str] = []
    lines.extend(build_overview(documents))
    lines.extend(build_paper_pages(documents, output_markdown.parent))
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    args = parse_args()
    manifest = load_json(args.manifest)
    output = Path(args.output_markdown).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_starter(manifest, output), encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
