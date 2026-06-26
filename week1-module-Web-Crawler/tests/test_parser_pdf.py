"""测试 PDF 文本与通用文本过滤逻辑。"""

from crawler.models import SourceConfig
from crawler.parser import parse_policy_pdf


def test_parse_policy_pdf_accepts_policy_text() -> None:
    """PDF 文本只要有足够政策信号，就应进入结构化结果。"""

    source = SourceConfig(
        source_id="ems",
        company="中国邮政",
        source_type="carrier",
        country_region="CN",
        base_url="https://example.com",
        entry_urls=["https://example.com/rules.pdf"],
        allowed_topics=["禁限寄", "危险品", "邮寄保险", "保价赔付"],
    )
    pdf_text = (
        "中国邮政禁寄和限寄规则 2025-01-01。"
        "本规则说明危险品、锂电池、保价赔付和理赔时限。"
        "寄件人应遵守包装要求、保险声明价值要求和禁寄目录。"
    )

    record, filtered = parse_policy_pdf(source, "https://example.com/rules.pdf", pdf_text)

    assert filtered is None
    assert record is not None
    assert "禁限寄" in record.policy_categories or "危险品" in record.policy_categories
