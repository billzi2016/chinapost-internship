"""Web 页面 Django app 配置。"""

from django.apps import AppConfig


class WebConfig(AppConfig):
    """注册 `apps.web`，提供聊天页面模板渲染和静态上下文。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.web"
