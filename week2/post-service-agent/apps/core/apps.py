"""核心数据模型 Django app 配置。"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """注册 `apps.core`，提供会话、消息、RAG 文档、引用和工单模型。"""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
