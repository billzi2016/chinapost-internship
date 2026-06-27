#!/usr/bin/env python3
"""将项目 Markdown 报告批量导出为高质量 PDF。

本脚本采用的不是 pandoc + xelatex 路线，而是：

1. Markdown -> HTML
2. HTML -> Chromium 无头浏览器打印 PDF

这样做的原因很直接：
- 对中文标题、正文、列表、引用块的渲染更自然
- 对图片较多的报告更友好
- 最终 PDF 更接近平时在浏览器里看到的文档效果
- 对 Markdown 风格文档来说，整体观感通常优于 LaTeX 硬排

当前脚本会导出：
- step1：模型选型、数据集分析与网页爬虫训练样本
- step2：LoRA 微调

输出 PDF 会落盘到 reports/step1_模型选型与数据集分析 和 reports/step2_lora微调。
"""

from __future__ import annotations

import html
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from markdown import markdown
from playwright.sync_api import sync_playwright


# 统一定位目录，避免到处手写相对路径。
REPORTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = REPORTS_DIR.parent
WEEK1_DIR = PROJECT_DIR / "week1"
WEB_CRAWLER_DIR = PROJECT_DIR / "week1-module-Web-Crawler"
WEEK3_DIR = PROJECT_DIR / "week3"
STEP1_DIR = REPORTS_DIR / "step1_模型选型与数据集分析"
STEP2_DIR = REPORTS_DIR / "step2_lora微调"


# 这里维护“输入 Markdown -> 输出 PDF”的映射关系。
# 后面如果要继续增加报告，只需要往这个列表里加一项即可。
REPORT_SPECS = [
    {
        "id": "week1-model-selection",
        "source": WEEK1_DIR / "第一版" / "docs" / "模型选型报告.md",
        "output": STEP1_DIR / "中文邮政客服任务开源大模型选型研究报告.pdf",
        "title": "中文邮政客服任务开源大模型选型研究报告",
    },
    {
        "id": "week1-sft-risk",
        "source": WEEK1_DIR / "第一版" / "docs" / "SFT训练与风险控制.md",
        "output": STEP1_DIR / "中文邮政客服任务SFT训练方案与风险控制报告.pdf",
        "title": "中文邮政客服任务SFT训练方案与风险控制报告",
    },
    {
        "id": "week1-csds-stats",
        "source": WEEK1_DIR / "第一版" / "stats" / "outputs" / "report.md",
        "output": STEP1_DIR / "CSDS数据集统计分析与关键词提取结果报告.pdf",
        "title": "CSDS数据集统计分析与关键词提取结果报告",
    },
    {
        "id": "week1-postal-filter",
        "source": WEEK1_DIR / "第一版" / "filter" / "outputs" / "report.md",
        "output": STEP1_DIR / "邮政相关对话筛选与向量空间可视化结果报告.pdf",
        "title": "邮政相关对话筛选与向量空间可视化结果报告",
    },
    {
        "id": "week1-classification-cases",
        "source": WEEK1_DIR / "第二版" / "01_分类效果评估与边界case分析" / "outputs" / "report.md",
        "output": STEP1_DIR / "分类效果评估与边界case分析报告.pdf",
        "title": "分类效果评估与边界 case 分析报告",
    },
    {
        "id": "week1-cluster-labels",
        "source": WEEK1_DIR / "第二版" / "04_可视化聚类与标签优化" / "outputs" / "report.md",
        "output": STEP1_DIR / "可视化聚类与标签优化报告.pdf",
        "title": "可视化聚类与标签优化报告",
    },
    {
        "id": "week1-training-samples",
        "source": WEB_CRAWLER_DIR / "report" / "training_samples_report.md",
        "output": STEP1_DIR / "邮政FAQ爬虫训练样本构建报告.pdf",
        "title": "邮政 FAQ 爬虫训练样本构建报告",
    },
    {
        "id": "week3-qwen25-full",
        "source": WEEK3_DIR / "reports" / "qwen2.5_mlx_sft_full_experiment_report.md",
        "output": STEP2_DIR / "基于AppleMLX的Qwen2.5邮政客服模型微调完整实验报告.pdf",
        "title": "基于 Apple MLX 的 Qwen2.5 邮政客服模型微调完整实验报告",
    },
    {
        "id": "week3-qwen25-3b-rank-sweep",
        "source": WEEK3_DIR / "reports" / "qwen2.5-3b_rank_sweep_report.md",
        "output": STEP2_DIR / "Qwen2.5-3B邮政客服LoRA RankSweep实验报告.pdf",
        "title": "Qwen2.5-3B 邮政客服 LoRA Rank Sweep 实验报告",
    },
    {
        "id": "week3-qwen25-7b-rank-sweep",
        "source": WEEK3_DIR / "reports" / "qwen2.5-7b_rank_sweep_report.md",
        "output": STEP2_DIR / "Qwen2.5-7B邮政客服LoRA RankSweep实验报告.pdf",
        "title": "Qwen2.5-7B 邮政客服 LoRA Rank Sweep 实验报告",
    },
]


# 这里直接内嵌一套打印样式，避免额外维护独立 CSS 文件。
# 设计目标不是花哨，而是“稳、清楚、适合中文报告打印”。
BASE_CSS = """
@page {
  size: A4;
  margin: 18mm 16mm 18mm 16mm;
}

html, body {
  font-family: "PingFang SC", "Hiragino Sans GB", "Heiti SC", "Noto Sans CJK SC",
               "Microsoft YaHei", sans-serif;
  color: #1f2328;
  background: #ffffff;
  line-height: 1.72;
  font-size: 13.5px;
}

body {
  margin: 0;
  padding: 0;
}

.report-root {
  max-width: 920px;
  margin: 0 auto;
}

h1, h2, h3, h4 {
  color: #111827;
  line-height: 1.35;
  font-weight: 700;
  page-break-after: avoid;
  break-after: avoid-page;
}

h1 {
  font-size: 26px;
  margin: 0 0 18px 0;
  padding-bottom: 10px;
  border-bottom: 2px solid #d0d7de;
}

h2 {
  font-size: 20px;
  margin-top: 30px;
  margin-bottom: 14px;
  padding-left: 10px;
  border-left: 4px solid #2563eb;
}

h3 {
  font-size: 16px;
  margin-top: 22px;
  margin-bottom: 10px;
}

h4 {
  font-size: 14px;
  margin-top: 16px;
  margin-bottom: 8px;
}

p {
  margin: 10px 0;
  text-align: justify;
}

ul, ol {
  margin: 10px 0 10px 24px;
  padding: 0;
}

li {
  margin: 4px 0;
}

blockquote {
  margin: 14px 0;
  padding: 10px 14px;
  background: #f6f8fa;
  border-left: 4px solid #94a3b8;
  color: #334155;
}

code {
  font-family: "SFMono-Regular", "Menlo", "Monaco", "Consolas", monospace;
  font-size: 0.92em;
  padding: 0.12em 0.34em;
  border-radius: 4px;
  background: #f3f4f6;
}

pre {
  overflow-wrap: anywhere;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 12px 14px;
  border-radius: 8px;
  background: #0f172a;
  color: #e5e7eb;
}

pre code {
  background: transparent;
  color: inherit;
  padding: 0;
  white-space: inherit;
  overflow-wrap: inherit;
  word-break: inherit;
}

img {
  display: block;
  max-width: 100%;
  max-height: 92vh;
  height: auto;
  margin: 12px auto 18px auto;
  border: 1px solid #d0d7de;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
  page-break-inside: avoid;
  break-inside: avoid;
}

hr {
  border: none;
  border-top: 1px solid #d0d7de;
  margin: 28px 0;
}

a {
  color: #1d4ed8;
  text-decoration: none;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin: 14px 0;
  font-size: 13px;
}

th, td {
  border: 1px solid #d0d7de;
  padding: 8px 10px;
  vertical-align: top;
}

th {
  background: #f3f4f6;
  font-weight: 700;
}

"""


def ensure_dependencies() -> None:
    """检查运行依赖是否已经安装。

    这里主要检查两类依赖：
    1. Python 依赖：markdown / playwright
       - 由于已经成功 import，因此不需要重复检查版本
    2. 浏览器运行时：Chromium
       - Playwright 安装 python 包之后，还需要额外装浏览器本体
    """

    # 这里用 Playwright 自带浏览器目录是否存在来做一个轻量检查。
    # 如果后续你更新了 Playwright，本检查依然能比较稳地工作。
    cache_root = Path.home() / "Library" / "Caches" / "ms-playwright"
    if not cache_root.exists():
        raise RuntimeError(
            "未检测到 Playwright 浏览器运行时。请先执行：\n"
            "playwright install chromium"
        )


def render_markdown_to_html(source: Path, title: str) -> str:
    """将单份 Markdown 文档渲染为完整 HTML。

    关键点：
    - 这里用 Python markdown 库做 Markdown -> HTML
    - 再手动包一层完整 HTML 模板
    - `base_url` 会在浏览器渲染时指定，因此相对图片路径可以正常工作
    """

    text = source.read_text(encoding="utf-8")
    body_html = markdown(
        text,
        extensions=[
            "extra",
            "tables",
            "fenced_code",
            "codehilite",
            "toc",
            "sane_lists",
        ],
        output_format="html5",
    )

    escaped_title = html.escape(title)
    base_href = source.parent.resolve().as_uri() + "/"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escaped_title}</title>
    <base href="{html.escape(base_href)}" />
    <style>{BASE_CSS}</style>
  </head>
  <body>
    <main class="report-root">
      {body_html}
    </main>
  </body>
</html>
"""


def convert_one_report(browser, source: Path, output: Path, title: str) -> None:
    """转换单份 Markdown 报告为 PDF。

    这里直接用浏览器渲染的原因：
    - 能更好处理 Markdown 图片
    - 中文字体更自然
    - 渲染结果更接近平时阅读 Markdown 的样式
    """

    if not source.exists():
        raise FileNotFoundError(f"未找到输入 Markdown：{source}")

    html_content = render_markdown_to_html(source, title)
    output.parent.mkdir(parents=True, exist_ok=True)

    # 这里不再直接用 set_content 渲染 HTML 字符串，
    # 而是先把 HTML 落成临时文件，再让 Chromium 以 file:// 方式打开。
    # 这样浏览器会按真实文件系统路径解析相对图片资源，
    # 对 report.md 里大量 `vis/*.png` 的本地图片更稳。
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".html",
        delete=False,
    ) as temp_file:
        temp_file.write(html_content)
        temp_html_path = Path(temp_file.name)

    page = browser.new_page()
    try:
        page.goto(temp_html_path.resolve().as_uri(), wait_until="networkidle")

        page.pdf(
            path=str(output),
            format="A4",
            print_background=True,
            margin={
                "top": "16mm",
                "right": "14mm",
                "bottom": "16mm",
                "left": "14mm",
            },
            prefer_css_page_size=True,
        )
    finally:
        page.close()
        temp_html_path.unlink(missing_ok=True)


def parse_args(argv: list[str]) -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(
        description="将项目 Markdown 报告导出为 PDF。",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出可渲染报告的 id，不生成 PDF。",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="ID",
        help="只渲染指定 id 的报告；不传则渲染全部。",
    )
    return parser.parse_args(argv)


def select_report_specs(only_ids: list[str] | None) -> list[dict[str, object]]:
    """根据 --only 参数选择要渲染的报告。"""

    if not only_ids:
        return REPORT_SPECS

    specs_by_id = {str(spec["id"]): spec for spec in REPORT_SPECS}
    unknown_ids = [report_id for report_id in only_ids if report_id not in specs_by_id]
    if unknown_ids:
        available = "\n".join(f"- {report_id}" for report_id in specs_by_id)
        unknown = ", ".join(unknown_ids)
        raise ValueError(f"未知报告 id：{unknown}\n\n可用 id：\n{available}")

    return [specs_by_id[report_id] for report_id in only_ids]


def print_report_specs() -> None:
    """打印可渲染报告清单。"""

    for spec in REPORT_SPECS:
        print(f"{spec['id']}\t{spec['title']}")


def main(argv: list[str] | None = None) -> int:
    """主入口。

    执行流程：
    1. 检查依赖
    2. 启动 Chromium 无头浏览器
    3. 逐份报告渲染并导出 PDF
    4. 输出完成信息
    """

    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)

        if args.list:
            print_report_specs()
            return 0

        selected_specs = select_report_specs(args.only)
        ensure_dependencies()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for spec in selected_specs:
                    source = Path(spec["source"])
                    output = Path(spec["output"])
                    title = str(spec["title"])
                    print(f"开始生成 PDF：{source.name} -> {output.name}")
                    convert_one_report(browser, source, output, title)
                    print(f"已生成：{output}")
            finally:
                browser.close()

        print(f"\nPDF 已生成完成，共 {len(selected_specs)} 份。")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\n生成失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
