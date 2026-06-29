#!/usr/bin/env python3
"""根据 final-result/dataset.jsonl 生成训练样本 Markdown 报告。"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from markdown import markdown as render_markdown


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR.parent / "final-result" / "dataset.jsonl"
OUTPUT_PATH = BASE_DIR / "training_samples_report.md"
FINAL_RESULT_DIR = BASE_DIR.parent / "final-result"


def load_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in DATASET_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def get_locator(row: dict[str, object]) -> str:
    return str(row.get("uri") or row.get("url") or "")


def format_summary(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "（空）"
    return text


def extract_answer_text(row: dict[str, object]) -> str:
    candidates = [
        str(row.get("summary", "") or "").strip(),
        str(row.get("evidence_text", "") or "").strip(),
    ]

    for text in candidates:
        if not text:
            continue
        if "答案：" in text:
            answer = text.split("答案：", 1)[1].strip()
            return answer or text
        return text

    return "（空）"


def format_value(value: object) -> str:
    if isinstance(value, list):
        return "、".join(str(item) for item in value) if value else "无"
    if value is True:
        return "是"
    if value is False:
        return "否"
    text = str(value).strip()
    return text or "无"


def split_markdown_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        if raw_line.startswith("### "):
            if current_title:
                sections.append((current_title, current_lines))
            current_title = raw_line[4:].strip()
            current_lines = []
            continue
        if raw_line.startswith("## "):
            if current_title:
                sections.append((current_title, current_lines))
                current_title = ""
                current_lines = []
            continue
        if current_title:
            current_lines.append(raw_line)

    if current_title:
        sections.append((current_title, current_lines))
    return sections


def strip_section_separators(lines: list[str]) -> list[str]:
    stripped = list(lines)
    while stripped and not stripped[-1].strip():
        stripped.pop()
    while stripped and stripped[-1].strip() in {"---", "***", "___"}:
        stripped.pop()
        while stripped and not stripped[-1].strip():
            stripped.pop()
    return stripped


def render_playwright_original(row: dict[str, object]) -> str:
    locator = get_locator(row)
    if not locator or "#" not in locator:
        return f"> {format_summary(str(row.get('evidence_text', '')))}"

    relative_path, _anchor = locator.split("#", 1)
    source_path = FINAL_RESULT_DIR / relative_path
    if not source_path.exists():
        return f"> {format_summary(str(row.get('evidence_text', '')))}"

    source_text = source_path.read_text(encoding="utf-8")
    target_title = str(row.get("title", "")).strip()

    for section_title, lines in split_markdown_sections(source_text):
        if section_title.strip() != target_title:
            continue

        body = "\n".join(strip_section_separators(lines)).strip()
        if not body:
            return f"> {format_summary(str(row.get('evidence_text', '')))}"

        body_html = render_markdown(
            body,
            extensions=[
                "tables",
                "fenced_code",
                "codehilite",
            ],
        )
        body_html = body_html.replace("<hr />", "").replace("<hr>", "")
        return f"<blockquote>\n{body_html}\n</blockquote>"

    return f"> {format_summary(str(row.get('evidence_text', '')))}"


def build_overview(rows: list[dict[str, object]]) -> str:
    source_counter = Counter(str(row.get("source_id", "")) for row in rows)
    company_counter = Counter(str(row.get("company", "")) for row in rows)

    lines = [
        "## 2. 数据文件概况",
        "",
        "输入文件：",
        "",
        "```text",
        "week1-module-Web-Crawler/final-result/dataset.jsonl",
        "```",
        "",
        f"文件格式为 JSON Lines，一行是一条训练样本。当前共包含 **{len(rows)}** 条样本，来源包括原始 EMS FAQ 结构化页面，以及基于 Playwright 图形化抓取流程整理出的扩展页面材料。",
        "",
        "| 项目 | 内容 |",
        "|---|---|",
        f"| 样本数量 | {len(rows)} |",
        f"| 数据来源 | {', '.join(source_counter.keys())} |",
        f"| 来源标识统计 | " + "；".join(f"`{k}`: {v}" for k, v in source_counter.items()) + " |",
        f"| 公司字段统计 | " + "；".join(f"`{k}`: {v}" for k, v in company_counter.items()) + " |",
        "| 文件格式 | JSONL |",
        "| 主要用途 | 邮政客服知识抽取、SFT 样本构造、评测题构造、RAG 知识库入库 |",
        "",
    ]
    return "\n".join(lines)


def build_field_section(rows: list[dict[str, object]]) -> str:
    sample = rows[0]
    keys = list(sample.keys())
    field_desc = {
        "source_id": "数据源标识。",
        "company": "所属来源或机构字段。",
        "url": "原始页面链接或原始 FAQ 锚点链接。",
        "uri": "本地原始 Markdown 文件路径及段落锚点。",
        "title": "样本标题，可作为用户问题或知识点标题。",
        "published_at": "发布时间，当前多数样本为空。",
        "policy_categories": "业务类别标签。",
        "summary": "适合直接转为训练答案的摘要。",
        "evidence_text": "原始证据文本，用于追溯和核验。",
        "insurance_available": "是否涉及可保价或保险服务。",
        "insurance_type": "保险或保价类型，未知时为 `未知`。",
        "compensation_limit": "赔付上限。",
        "claim_deadline": "申诉或理赔期限。",
        "requirements": "办理要求或材料要求。",
        "insurance_exclusions": "保险或赔付排除项。",
    }

    lines = [
        "## 3. 字段结构",
        "",
        f"当前数据集中统一可见字段共 **{len(keys)}** 个：",
        "",
        "| 字段 | 类型 | 含义 |",
        "|---|---|---|",
    ]
    for key in keys:
        value = sample[key]
        if isinstance(value, list):
            field_type = "list"
        elif isinstance(value, bool):
            field_type = "bool"
        else:
            field_type = type(value).__name__
        lines.append(f"| `{key}` | {field_type} | {field_desc.get(key, '字段说明待补充。')} |")

    lines.extend(
        [
            "",
            "字段设计上仍然保留了“原文证据”和“结构化业务字段”两类信息。`summary` 更适合直接进入训练数据，`evidence_text` 用于追溯；而 `source_id`、`url`/`uri` 则让后续样本回溯到网页 FAQ 或 Playwright 页面材料成为可能。",
            "",
        ]
    )
    return "\n".join(lines)


def build_source_section(rows: list[dict[str, object]]) -> str:
    source_counter = Counter(str(row.get("source_id", "")) for row in rows)
    lines = [
        "## 4. 来源拆分与 Playwright 扩展说明",
        "",
        "当前数据已经不再只是最初的 EMS FAQ 小样本，而是由两类来源共同组成：",
        "",
        "| 来源标识 | 样本数 | 说明 |",
        "|---|---:|---|",
    ]
    for source_id, count in source_counter.items():
        if source_id == "ems_policy_network":
            desc = "原始 EMS FAQ / 结构化网页问答样本。"
        elif source_id == "playwright_mcp":
            desc = "通过 Playwright 图形化页面抓取流程整理出的扩展页面材料样本。"
        else:
            desc = "其他来源。"
        lines.append(f"| `{source_id}` | {count} | {desc} |")

    lines.extend(
        [
            "",
            "其中 `playwright_mcp` 这部分样本的特点，不再只是直接读取公开 FAQ 接口，而是通过图形化浏览、页面渲染、必要时结合 OCR 辅助提取页面文本，再整理成可训练的结构化片段。",
            "",
            "这类页面通常出现在以下场景：",
            "",
            "- 页面本身依赖前端渲染，直接请求接口拿不到正文。",
            "- 海外访问、云环境访问或自动化访问时，容易遇到地区阻断或访问校验。",
            "- 页面存在图片化文本、扫描件、嵌入式 PDF 或复杂布局，需要 OCR 或视觉辅助提取。",
            "",
            "在实际采集过程中，海外阻断、WAF 风控和反爬策略常见的表现包括：",
            "",
            "- `403 Forbidden`：服务器明确拒绝访问，常见于地区限制、UA/Referer 校验或 WAF 拦截。",
            "- `412 Precondition Failed`：常见于请求头、签名、来源校验或反机器人策略触发。",
            "- `429 Too Many Requests`：访问频率过高，被限流。",
            "- `503 Service Unavailable`：站点临时不可用，或反爬策略返回伪装性服务不可用页面。",
            "- `521/522/524`：常见于 CDN 或上游站点连接异常、超时、回源失败。",
            "- 登录态缺失、验证码、人机验证页、JavaScript Challenge、Cloudflare/边缘防护页。",
            "",
            "因此，Playwright 这部分数据的价值，不只是补充了样本数量，更重要的是补充了“在真实复杂页面环境下如何获取证据文本”的能力边界。",
            "",
        ]
    )
    return "\n".join(lines)


def build_category_section(rows: list[dict[str, object]]) -> str:
    counter: Counter[str] = Counter()
    for row in rows:
        for category in row.get("policy_categories", []):
            counter[str(category)] += 1

    lines = [
        "## 5. 类别覆盖情况",
        "",
        f"当前 **{len(rows)}** 条样本覆盖了多个业务标签。由于一条样本可以带多个标签，因此标签计数总和大于样本数。",
        "",
        "| 类别 | 样本数 |",
        "|---|---:|",
    ]
    for category, count in counter.most_common():
        lines.append(f"| {category} | {count} |")

    lines.extend(
        [
            "",
            "相比最早只有少量 EMS FAQ 的阶段，当前数据已经从“产品介绍 + 国际清关 + 售后查询”扩展到更广的政策、条款、限制、边界、风控、末端投递与跨境运营场景。",
            "",
        ]
    )
    return "\n".join(lines)


def build_samples_section(rows: list[dict[str, object]]) -> str:
    lines = [
        "## 6. 全量样本清单",
        "",
        "下面按照 JSONL 中的顺序列出当前全部样本。每条样本都保留来源、类别、定位路径和摘要，便于后续人工抽检与继续筛样。",
        "",
    ]

    for idx, row in enumerate(rows, start=1):
        source_id = str(row.get("source_id", ""))
        lines.extend(
            [
                f"### 样本 {idx}：{format_value(row.get('title', ''))}",
                "",
                "| 字段 | 内容 |",
                "|---|---|",
                f"| 来源标识 | `{format_value(row.get('source_id'))}` |",
                f"| 公司字段 | {format_value(row.get('company'))} |",
                f"| 类别 | {format_value(row.get('policy_categories'))} |",
                f"| 是否涉及保险 | {format_value(row.get('insurance_available'))} |",
                f"| 标题 | {format_value(row.get('title'))} |",
                f"| 定位 | `{format_value(get_locator(row))}` |",
                "",
            ]
        )

        if source_id == "ems_policy_network":
            lines.extend(
                [
                    "问题：",
                    "",
                    f"> {format_summary(str(row.get('title', '')))}",
                    "",
                    "答案：",
                    "",
                    f"> {format_summary(extract_answer_text(row))}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "原文：",
                    "",
                    render_playwright_original(row),
                    "",
                ]
            )

    return "\n".join(lines)


def build_sft_section(rows: list[dict[str, object]]) -> str:
    source_counter = Counter(str(row.get("source_id", "")) for row in rows)
    lines = [
        "## 7. 可转化的 SFT 形式",
        "",
        "当前数据已经具备两类不同风格的训练原料：",
        "",
        f"- `ems_policy_network`：更像标准 FAQ 问答对，适合直接转单轮客服回复。",
        f"- `playwright_mcp`：更像条款片段、政策段落和页面证据材料，适合转成“基于原文证据回答”的长答案样本。",
        "",
        f"当前来源拆分为：`ems_policy_network` {source_counter.get('ems_policy_network', 0)} 条，`playwright_mcp` {source_counter.get('playwright_mcp', 0)} 条。",
        "",
        "### 7.1 单轮问答",
        "",
        "适合产品介绍、时限解释、清关流程说明。",
        "",
        "```json",
        '{"messages":[{"role":"system","content":"你是中国邮政 EMS 客服助手，回答必须基于官方 FAQ，不确定时引导用户查询官方渠道。"},{"role":"user","content":"即日专递是什么？能当天送到吗？"},{"role":"assistant","content":"即日专递业务面向所有用户开办，主要依托自主运输网，在特定线路提供当日上午寄件、当日送达的寄递服务，以同城流向为主。具体开办范围建议进入人工客服或官方渠道查询。"}]}',
        "```",
        "",
        "### 7.2 条款型长回答",
        "",
        "适合 Playwright 抓到的协议、限制、边界与理赔规则页面。",
        "",
        "```json",
        '{"messages":[{"role":"system","content":"你是中国邮政业务规则助手，回答必须优先基于提供的政策证据，不要编造超出原文的承诺。"},{"role":"user","content":"未保价邮件丢失后怎么赔？"},{"role":"assistant","content":"根据现有样本，未保价邮件的赔偿通常仍受产品规则、邮资倍数或标准赔偿条款约束，具体以实际适用的服务协议和官方公示口径为准。如果需要准确判断，建议结合具体产品类型、是否保价、受理渠道和正式条款进一步确认。"}]}',
        "```",
        "",
        "### 7.3 边界控制问答",
        "",
        "适合关税、清关、赔付等不能由模型自行承诺的场景。",
        "",
        "这些样本最重要的价值，不只是回答问题本身，而是训练模型知道什么时候必须收束回答边界，什么时候应该回到“以海关/官方页面/正式条款为准”。",
        "",
    ]
    return "\n".join(lines)


def build_conclusion(rows: list[dict[str, object]]) -> str:
    return "\n".join(
        [
            "## 8. 结论",
            "",
            f"当前 `dataset.jsonl` 已经从最初的 11 条 EMS FAQ 小样本，扩展为 **{len(rows)}** 条混合来源训练样本。",
            "",
            "这批数据的意义主要体现在三点：",
            "",
            "1. 保留了原始 EMS FAQ 的标准客服问答能力。",
            "2. 引入了 Playwright 图形化抓取和 OCR 辅助整理的页面材料，覆盖了更复杂的协议、条款和限制场景。",
            "3. 显式补齐了真实网页环境中的阻断、反爬、海外访问受限和复杂渲染页面问题，让数据来源更贴近真实业务采集难点。",
            "",
            "如果下一步继续扩展，最值得优先补充的是：",
            "",
            "- 对 Playwright 来源样本再做一轮“可训练化”清洗，把长条款拆成更稳定的问答对。",
            "- 对可能存在历史口径或地区差异的条款继续做来源核验。",
            "- 对 `summary` 做进一步标准化，减少过长段落直接进入训练时的噪声。",
            "",
        ]
    )


def build_report(rows: list[dict[str, object]]) -> str:
    parts = [
        "# 邮政 FAQ 训练样本构建报告",
        "",
        "## 1. 报告目标",
        "",
        "本报告分析 `week1-module-Web-Crawler/final-result/dataset.jsonl` 中当前已经整理完成的邮政训练样本。该文件由原始 EMS FAQ 结构化样本与基于 Playwright 图形化采集流程扩展得到的页面材料共同组成，目标是把公开网页、FAQ、协议和限制页面中的可用内容整理成结构化样本，为后续邮政客服模型的 SFT、评估集构造和知识库入库提供基础数据。",
        "",
        "这份报告不只记录样本条数，而是完整说明：",
        "",
        "1. 当前数据集的规模与来源拆分。",
        "2. 每条 JSONL 样本包含哪些字段。",
        "3. Playwright 扩展样本与原始 EMS FAQ 样本的区别。",
        "4. 当前类别覆盖和全量样本清单。",
        "5. 这些样本如何继续转化为更可用的 SFT 数据。",
        "",
        build_overview(rows),
        build_field_section(rows),
        build_source_section(rows),
        build_category_section(rows),
        build_samples_section(rows),
        build_sft_section(rows),
        build_conclusion(rows),
    ]
    return "\n".join(parts).strip() + "\n"


def main() -> int:
    rows = load_rows()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_report(rows), encoding="utf-8")
    print(f"wrote report for {len(rows)} samples to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
