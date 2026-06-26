"""测试政策链接发现逻辑。"""

from crawler.link_discovery import discover_policy_links


def test_discover_policy_links_keeps_same_domain_policy_urls() -> None:
    """应只保留同域且像政策页面的链接。"""

    html = """
    <a href="/service/terms">服务条款</a>
    <a href="/policy/prohibited-items">禁寄物品</a>
    <a href="https://other.example.com/policy">其他域名</a>
    <a href="/product/list">产品列表</a>
    """

    links = discover_policy_links("https://example.com/", html)

    assert "https://example.com/service/terms" in links
    assert "https://example.com/policy/prohibited-items" in links
    assert "https://other.example.com/policy" not in links
    assert "https://example.com/product/list" not in links


def test_discover_policy_links_skips_static_assets() -> None:
    """静态资源路径不应被误认为政策页面。"""

    html = """
    <a href="/xhtml/libs/idangerous.swiper.css">css</a>
    <a href="/policy/dangerous-goods.html">危险品规则</a>
    """

    links = discover_policy_links("https://example.com/", html)

    assert "https://example.com/xhtml/libs/idangerous.swiper.css" not in links
    assert "https://example.com/policy/dangerous-goods.html" in links


def test_discover_policy_links_keeps_policy_pdf() -> None:
    """带政策语义的 PDF 应保留下来，供后续下载解析。"""

    html = """
    <a href="/files/prohibited-items.pdf">禁寄目录 PDF</a>
    <a href="/files/manual.pdf">用户手册</a>
    """

    links = discover_policy_links("https://example.com/", html)

    assert "https://example.com/files/prohibited-items.pdf" in links
    assert "https://example.com/files/manual.pdf" not in links


def test_discover_policy_links_skips_generic_claim_page() -> None:
    """只有宽泛 claim 语义的帮助页不应直接进入候选队列。"""

    html = """
    <a href="/help/claim">Claim support</a>
    <a href="/support/insurance">Insurance coverage</a>
    """

    links = discover_policy_links("https://example.com/", html)

    assert "https://example.com/help/claim" not in links
    assert "https://example.com/support/insurance" in links
