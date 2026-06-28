"""加载项目配置文件。

本文件的目标是把 `configs/` 下的 YAML 配置转换成结构化对象，
并在配置缺失或字段异常时尽早报错，避免问题拖到抓取过程中才暴露。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from crawler.models import RateLimitConfig, SourceConfig


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """读取单个 YAML 文件并返回字典。

    参数:
    - path: 配置文件路径。

    返回:
    - 解析后的字典对象。

    异常:
    - FileNotFoundError: 配置文件不存在。
    - RuntimeError: 当前环境缺少 YAML 解析依赖。
    - ValueError: 文件内容为空或格式不符合预期。
    """

    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 PyYAML 依赖，无法读取 YAML 配置文件。") from exc

    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(f"配置文件格式不正确，预期为字典: {path}")

    return data


def load_sources(config_dir: Path) -> list[SourceConfig]:
    """加载来源配置列表。"""

    raw_data = _load_yaml_file(config_dir / "sources.yaml")
    sources = raw_data.get("sources", [])
    return [
        SourceConfig(
            source_id=item["source_id"],
            company=item["company"],
            source_type=item["source_type"],
            country_region=item["country_region"],
            base_url=item["base_url"],
            entry_urls=item["entry_urls"],
            allowed_topics=item["allowed_topics"],
            allowed_domains=item.get("allowed_domains", []),
            api_endpoints=item.get("api_endpoints", []),
            parser_hint=item.get("parser_hint", "generic"),
        )
        for item in sources
    ]


def load_categories(config_dir: Path) -> dict[str, Any]:
    """加载政策分类和关键词配置。"""

    return _load_yaml_file(config_dir / "categories.yaml")


def load_rate_limits(config_dir: Path) -> tuple[RateLimitConfig, dict[str, RateLimitConfig]]:
    """加载默认限速配置和域名级覆盖配置。"""

    raw_data = _load_yaml_file(config_dir / "rate_limits.yaml")
    defaults = raw_data["defaults"]
    default_config = RateLimitConfig(
        min_interval_seconds=defaults["min_interval_seconds"],
        max_interval_seconds=defaults["max_interval_seconds"],
        max_concurrency=defaults["max_concurrency"],
        user_agent=defaults["user_agent"],
    )

    domain_overrides: dict[str, RateLimitConfig] = {}
    for domain, override in raw_data.get("domains", {}).items():
        domain_overrides[domain] = RateLimitConfig(
            min_interval_seconds=override.get(
                "min_interval_seconds", default_config.min_interval_seconds
            ),
            max_interval_seconds=override.get(
                "max_interval_seconds", default_config.max_interval_seconds
            ),
            max_concurrency=override.get(
                "max_concurrency", default_config.max_concurrency
            ),
            user_agent=override.get("user_agent", default_config.user_agent),
        )

    return default_config, domain_overrides
