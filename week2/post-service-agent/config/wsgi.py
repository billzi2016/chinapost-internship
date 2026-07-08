"""WSGI 入口。

传统 Django 部署入口；本地 `manage.py runserver` 也会使用同一套 settings。
"""

from __future__ import annotations

import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
