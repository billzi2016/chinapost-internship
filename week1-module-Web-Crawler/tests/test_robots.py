"""测试 robots 规则判断逻辑。"""

from crawler.robots import RobotsManager


def test_robots_manager_respects_disallow_rules() -> None:
    """被 robots 禁止的路径应返回禁止结果。"""

    manager = RobotsManager()
    manager.preload_from_text(
        "https://example.com/private/page",
        "User-agent: *\nDisallow: /private/\n",
    )

    decision = manager.is_allowed(
        "https://example.com/private/page",
        "PolicyCrawler/0.1",
    )

    assert decision.allowed is False
