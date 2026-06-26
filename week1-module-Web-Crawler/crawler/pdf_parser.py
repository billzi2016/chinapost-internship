"""处理 PDF 文档解析。

PDF 经常是规则、条款、禁限寄目录等真实政策文本的主要载体，
因此这里提供一个尽量轻依赖但可落地的正文提取实现。
"""

from __future__ import annotations

from io import BytesIO


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """提取 PDF 文本。

    当前优先使用 `pypdf` 做逐页抽取。
    如果运行环境未安装依赖，会直接抛出明确错误，避免静默吞掉 PDF。
    """

    if not pdf_bytes:
        return ""

    try:
        from pypdf import PdfReader
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 pypdf 依赖，无法解析 PDF") from exc

    reader = PdfReader(BytesIO(pdf_bytes))
    text_parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_text = " ".join(page_text.split())
        if page_text:
            text_parts.append(page_text)
    return "\n".join(text_parts)
