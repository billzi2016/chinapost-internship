"""处理 PDF 文档解析。

当前阶段先保留接口，后续在确认依赖和样本 PDF 后再补充真正的文本提取。
保持独立文件是为了避免 HTML 和 PDF 解析逻辑混杂。
"""

from __future__ import annotations


def extract_pdf_text(_: bytes) -> str:
    """提取 PDF 文本。

    当前返回空字符串，提醒调用方该能力尚未实现。
    """

    return ""
