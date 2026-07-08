"""API Django app 配置。"""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """注册 `apps.api`，提供 django-ninja 路由和业务 API。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.api"
