#!/usr/bin/env python3
from __future__ import annotations

import uvicorn

from src.app_factory import build_app, build_state


STATE = build_state()
CONFIG = STATE.config
CONFIG_PATH = STATE.config_path
BEST_ADAPTER_PATH = STATE.adapter_path
app = build_app(STATE)


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=CONFIG.server.host,
        port=CONFIG.server.port,
        reload=False,
    )
