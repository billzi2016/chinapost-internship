"""定义配置、任务和采集结果的数据模型。

本文件只负责描述结构化数据，不承担网络请求、文件读写或解析逻辑。
这样做的目的是让各模块围绕统一的数据结构协作，避免参数在函数之间散落。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class SourceConfig:
    """描述一个可采集来源的基础配置。"""

    source_id: str
    company: str
    source_type: str
    country_region: str
    base_url: str
    entry_urls: list[str]
    allowed_topics: list[str]
    parser_hint: str = "generic"


@dataclass(slots=True)
class RateLimitConfig:
    """描述域名级别的限速配置。"""

    min_interval_seconds: int
    max_interval_seconds: int
    max_concurrency: int
    user_agent: str


@dataclass(slots=True)
class CrawlTask:
    """描述一个待抓取页面任务。"""

    source_id: str
    company: str
    url: str
    topic_hints: list[str] = field(default_factory=list)
    depth: int = 0


@dataclass(slots=True)
class RobotsDecision:
    """记录 robots 校验结果，便于后续审计和落盘。"""

    url: str
    allowed: bool
    checked_at: datetime
    reason: str


@dataclass(slots=True)
class FetchResult:
    """封装单次请求结果。

    当页面被 robots 拒绝、请求失败或被限流时，也通过该结构返回，
    这样调度层就不需要在多个异常分支里重复判断。
    """

    url: str
    status_code: int | None
    content_type: str
    text: str
    final_url: str
    fetched_at: datetime
    success: bool
    robots_allowed: bool
    robots_reason: str
    failure_reason: str = ""
    body_bytes: bytes = b""


@dataclass(slots=True)
class PolicyRecord:
    """描述解析后的政策记录。"""

    source_id: str
    company: str
    url: str
    title: str
    published_at: str
    policy_categories: list[str]
    summary: str
    evidence_text: str
    insurance_available: bool
    insurance_type: str
    compensation_limit: str
    claim_deadline: str
    requirements: list[str] = field(default_factory=list)
    insurance_exclusions: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FilteredPageRecord:
    """记录被过滤掉的页面，便于人工审计但不进入训练样本。"""

    source_id: str
    company: str
    url: str
    title: str
    filter_reason: str
    summary: str


@dataclass(slots=True)
class PdfDownloadRecord:
    """记录 PDF 原始文件保存位置，便于后续审计和复跑。"""

    source_id: str
    company: str
    url: str
    title: str
    saved_path: str
