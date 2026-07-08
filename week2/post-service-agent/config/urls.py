"""项目级 URL 入口。

这里把三类路由挂到同一个 Django 应用：
- `/admin/`：Django 管理后台；
- `/`：Web 聊天页面；
- `/api/`：django-ninja API 和 SSE 接口。
"""

from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from apps.api.urls import api


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.web.urls")),
    path("api/", api.urls),
]
