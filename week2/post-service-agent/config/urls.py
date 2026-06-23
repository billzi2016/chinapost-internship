from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

from apps.api.urls import api


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.web.urls")),
    path("api/", api.urls),
]
