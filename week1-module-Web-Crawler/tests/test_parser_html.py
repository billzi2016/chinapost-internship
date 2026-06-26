"""测试 HTML 页面解析与过滤逻辑。"""

from crawler.models import SourceConfig
from crawler.parser import parse_policy_page


def _build_source() -> SourceConfig:
    return SourceConfig(
        source_id="chinapost_policy",
        company="中国邮政",
        source_type="carrier",
        country_region="CN",
        base_url="https://example.com",
        entry_urls=["https://example.com/"],
        allowed_topics=["禁限寄", "国际清关", "邮寄保险", "保价赔付", "服务条款"],
    )


def test_parse_policy_page_filters_homepage_navigation() -> None:
    """官网首页不应仅因导航词被识别为政策页。"""

    html = """
    <html>
      <head><title>首页 - 中国邮政集团有限公司</title></head>
      <body>
        首页 个人服务 企业服务 新闻中心 关于我们 运单查询 网点查询
        北京邮政 天津邮政 河北邮政 广东邮政 中邮信息科技
      </body>
    </html>
    """

    record, filtered = parse_policy_page(_build_source(), "https://example.com/", html)

    assert record is None
    assert filtered is not None
    assert filtered.filter_reason in {"首页导航特征过强", "页面噪声过高", "导航页特征过强", "正文过短"}


def test_parse_policy_page_accepts_policy_detail_page() -> None:
    """真实政策详情页应保留下来。"""

    html = """
    <html>
      <head><title>禁寄物品和保价赔付规则</title></head>
      <body>
        <h1>禁寄物品和保价赔付规则</h1>
        <p>2025-06-01 发布。本规则说明危险品、锂电池、禁寄目录、声明价值和保价赔付要求。</p>
        <p>寄件人应提供价值证明，若发生破损或丢失，应在7日内提出索赔，最高赔偿1000元。</p>
      </body>
    </html>
    """

    record, filtered = parse_policy_page(
        _build_source(),
        "https://example.com/policy/prohibited-items",
        html,
    )

    assert filtered is None
    assert record is not None
    assert "禁限寄" in record.policy_categories
    assert record.insurance_available is True
