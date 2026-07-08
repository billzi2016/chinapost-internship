"""ASGI 入口。

当前项目主要用 Django runserver/WSGI 路径运行；保留 ASGI 入口方便未来接入异步服务器。
"""

from __future__ import annotations

import os

from django.core.asgi import get_asgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
