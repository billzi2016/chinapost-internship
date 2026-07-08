from __future__ import annotations

import re

from post_ai.agent_tools import get_current_date, get_current_time
from post_ai.agent_tools.time_tools import DEFAULT_TIMEZONE


def test_current_date_tool_returns_iso_date_for_utc() -> None:
    result = get_current_date("UTC")

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", result)


def test_current_time_tool_returns_clock_time_for_utc() -> None:
    result = get_current_time("UTC")

    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", result)


def test_time_tools_default_to_shanghai_timezone() -> None:
    assert DEFAULT_TIMEZONE == "Asia/Shanghai"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", get_current_date())
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", get_current_time())
