"""测试请求器中的跳转识别逻辑。"""

from crawler.fetcher import Fetcher
from crawler.models import RateLimitConfig
from crawler.robots import RobotsManager


def test_extract_client_side_redirect_from_script() -> None:
    """应能识别简单的 window.location.replace 跳转。"""

    fetcher = Fetcher(
        robots_manager=RobotsManager(),
        default_rate_limit=RateLimitConfig(1, 1, 1, "PolicyCrawler/0.1"),
        domain_rate_limits={},
    )

    redirect = fetcher._extract_client_side_redirect(
        "https://www.sf-express.com/",
        "<script>window.location.replace('chn/sc');</script>",
    )

    assert redirect == "https://www.sf-express.com/chn/sc"
