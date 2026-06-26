"""测试 URL 规范化和哈希构造逻辑。"""

from crawler.dedupe import build_content_hash, canonicalize_url


def test_canonicalize_url_orders_query_params() -> None:
    """相同查询参数顺序应得到相同规范 URL。"""

    first = canonicalize_url("https://Example.com/path?b=2&a=1")
    second = canonicalize_url("https://example.com/path?a=1&b=2")
    assert first == second


def test_build_content_hash_ignores_extra_spaces() -> None:
    """正文中多余空白不应影响内容哈希。"""

    first = build_content_hash("保险 条款   说明")
    second = build_content_hash("保险 条款 说明")
    assert first == second
