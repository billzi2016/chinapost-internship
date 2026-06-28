"""测试请求器中的跳转识别逻辑。"""

from crawler.fetcher import Fetcher
from crawler.models import RateLimitConfig


def test_extract_client_side_redirect_from_script() -> None:
    """应能识别简单的 window.location.replace 跳转。"""

    fetcher = Fetcher(
        default_rate_limit=RateLimitConfig(1, 1, 1, "PolicyCrawler/0.1"),
        domain_rate_limits={},
    )

    redirect = fetcher._extract_client_side_redirect(
        "https://www.sf-express.com/",
        "<script>window.location.replace('chn/sc');</script>",
    )

    assert redirect == "https://www.sf-express.com/chn/sc"


def test_resolve_rate_limit_matches_subdomain() -> None:
    """根域名限速配置应覆盖对应子域名。"""

    default = RateLimitConfig(1, 1, 1, "default")
    ems_limit = RateLimitConfig(15, 30, 1, "browser")
    fetcher = Fetcher(default_rate_limit=default, domain_rate_limits={"ems.com.cn": ems_limit})

    assert fetcher._resolve_rate_limit("https://www.ems.com.cn/insured") is ems_limit
    assert fetcher._resolve_rate_limit("http://nmc.ems.com.cn:9096/imcloud/static/lead.html") is ems_limit
    assert fetcher._resolve_rate_limit("https://example.com/policy") is default


def test_detects_ems_waf_block_page() -> None:
    """EMS 安全设备阻断页应被标记为 WAF 阻断。"""

    fetcher = Fetcher(
        default_rate_limit=RateLimitConfig(1, 1, 1, "browser"),
        domain_rate_limits={},
    )
    response_data = {
        "status_code": 405,
        "content_type": "text/html",
        "text": "很抱歉，由于您访问的URL有可能对网站造成安全威胁，您的访问被阻断。",
        "final_url": "https://www.ems.com.cn/insured",
        "body_bytes": b"",
    }

    assert fetcher._is_waf_blocked_response(response_data) is True


def test_detects_ems_412_as_waf_block() -> None:
    """EMS 返回 412 时也应进入浏览器 fallback 路径。"""

    fetcher = Fetcher(
        default_rate_limit=RateLimitConfig(1, 1, 1, "browser"),
        domain_rate_limits={},
    )
    response_data = {
        "status_code": 412,
        "content_type": "text/html",
        "text": "",
        "final_url": "https://www.ems.com.cn/Taboo_items",
        "body_bytes": b"",
    }

    assert fetcher._is_waf_blocked_response(response_data) is True
