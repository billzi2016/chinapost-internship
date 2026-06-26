"""处理 robots.txt 校验与缓存。

这里不实现抓取逻辑，只负责确认某个 URL 是否允许访问。
这样请求器在发起真实网络请求之前，可以统一调用本模块完成合规检查。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import threading
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

from crawler.models import RobotsDecision


@dataclass(slots=True)
class RobotsEntry:
    """缓存单个域名的 robots 解析器和最近拉取时间。"""

    parser: RobotFileParser
    loaded_at: datetime


class RobotsManager:
    """统一管理 robots 规则。

    设计意图:
    - 对同一个域名复用 robots 解析器，避免重复请求。
    - 在读取失败时给出保守结果，保证调度层能继续处理其他来源。
    """

    def __init__(self) -> None:
        self._cache: dict[str, RobotsEntry] = {}
        self._lock = threading.Lock()

    def _build_robots_url(self, url: str) -> str:
        """根据目标 URL 生成对应的 robots.txt 地址。"""

        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def preload_from_text(self, target_url: str, robots_text: str) -> None:
        """向缓存中注入 robots 内容，主要用于测试。"""

        parser = RobotFileParser()
        parser.set_url(self._build_robots_url(target_url))
        parser.parse(robots_text.splitlines())
        self._cache[urlparse(target_url).netloc] = RobotsEntry(
            parser=parser,
            loaded_at=datetime.utcnow(),
        )

    def ensure_parser(self, url: str) -> RobotFileParser:
        """获取指定 URL 对应域名的 robots 解析器。"""

        parsed = urlparse(url)
        domain = parsed.netloc
        with self._lock:
            cached = self._cache.get(domain)
            if cached is not None:
                return cached.parser

            parser = RobotFileParser()
            robots_url = self._build_robots_url(url)
            parser.set_url(robots_url)
            robots_text = self._fetch_robots_text(robots_url)
            parser.parse(robots_text.splitlines())
            self._cache[domain] = RobotsEntry(parser=parser, loaded_at=datetime.utcnow())
            return parser

    def _fetch_robots_text(self, robots_url: str) -> str:
        """以显式超时方式抓取 robots.txt。

        标准库自带的 `RobotFileParser.read()` 不方便设置超时。
        全量扫描时如果少数站点握手很慢，会拖住整个流程，因此这里自行请求。
        """

        request = Request(
            robots_url,
            headers={"User-Agent": "PolicyCrawler/0.1 (+policy-crawler@example.com)"},
        )
        with urlopen(request, timeout=10.0) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    def is_allowed(self, url: str, user_agent: str) -> RobotsDecision:
        """判断 URL 是否允许抓取。

        这里把异常统一折叠为保守拒绝，避免在网络不稳定时误抓不该访问的页面。
        """

        try:
            parser = self.ensure_parser(url)
            allowed = parser.can_fetch(user_agent, url)
            reason = "robots 允许抓取" if allowed else "robots 禁止抓取"
            return RobotsDecision(
                url=url,
                allowed=allowed,
                checked_at=datetime.utcnow(),
                reason=reason,
            )
        except Exception as exc:
            return RobotsDecision(
                url=url,
                allowed=False,
                checked_at=datetime.utcnow(),
                reason=f"robots 校验失败，按保守策略跳过: {exc}",
            )
