#!/usr/bin/env python3
"""将 week1 的核心 Markdown 报告批量导出为高质量 PDF。

本脚本采用的不是 pandoc + xelatex 路线，而是：

1. Markdown -> HTML
2. HTML -> Chromium 无头浏览器打印 PDF

这样做的原因很直接：
- 对中文标题、正文、列表、引用块的渲染更自然
- 对图片较多的报告更友好
- 最终 PDF 更接近平时在浏览器里看到的文档效果
- 对 Markdown 风格文档来说，整体观感通常优于 LaTeX 硬排

脚本会自动处理以下四份文档：
1. docs/模型选型报告.md
2. docs/SFT训练与风险控制.md
3. stats/outputs/report.md
4. filter/outputs/report.md

输出 PDF 会统一落盘到 week1/reports 目录。
"""

from __future__ import annotations

import html
import shutil
import sys
from pathlib import Path

from markdown import markdown
from playwright.sync_api import sync_playwright


# 统一定位目录，避免到处手写相对路径。
REPORTS_DIR = Path(__file__).resolve().parent
WEEK1_DIR = REPORTS_DIR.parent


# 这里维护“输入 Markdown -> 输出 PDF”的映射关系。
# 后面如果要继续增加报告，只需要往这个列表里加一项即可。
REPORT_SPECS = [
    {
        "source": WEEK1_DIR / "docs" / "模型选型报告.md",
        "output": REPORTS_DIR / "中文邮政客服任务开源大模型选型研究报告.pdf",
        "title": "中文邮政客服任务开源大模型选型研究报告",
    },
    {
        "source": WEEK1_DIR / "docs" / "SFT训练与风险控制.md",
        "output": REPORTS_DIR / "中文邮政客服任务SFT训练方案与风险控制报告.pdf",
        "title": "中文邮政客服任务SFT训练方案与风险控制报告",
    },
    {
        "source": WEEK1_DIR / "stats" / "outputs" / "report.md",
        "output": REPORTS_DIR / "CSDS数据集统计分析与关键词提取结果报告.pdf",
        "title": "CSDS数据集统计分析与关键词提取结果报告",
    },
    {
        "source": WEEK1_DIR / "filter" / "outputs" / "report.md",
        "output": REPORTS_DIR / "邮政相关对话筛选与向量空间可视化结果报告.pdf",
        "title": "邮政相关对话筛选与向量空间可视化结果报告",
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
  overflow-x: auto;
  padding: 12px 14px;
  border-radius: 8px;
  background: #0f172a;
  color: #e5e7eb;
}

pre code {
  background: transparent;
  color: inherit;
  padding: 0;
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

    page = browser.new_page()
    try:
        # HTML 头部已经通过 <base href="..."> 指定了相对资源解析目录，
        # 因此像 `vis/train_pca.png` 这类图片路径能被浏览器直接正确加载。
        page.set_content(html_content, wait_until="networkidle")

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


def main() -> int:
    """主入口。

    执行流程：
    1. 检查依赖
    2. 启动 Chromium 无头浏览器
    3. 逐份报告渲染并导出 PDF
    4. 输出完成信息
    """

    try:
        ensure_dependencies()
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for spec in REPORT_SPECS:
                    source = Path(spec["source"])
                    output = Path(spec["output"])
                    title = str(spec["title"])
                    print(f"开始生成 PDF：{source.name} -> {output.name}")
                    convert_one_report(browser, source, output, title)
                    print(f"已生成：{output}")
            finally:
                browser.close()

        print("\n全部 PDF 已生成完成。")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\n生成失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
