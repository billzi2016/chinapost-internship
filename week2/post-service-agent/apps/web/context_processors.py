"""模板上下文处理器。

用于给所有模板注入通用变量，当前主要提供静态资源版本号。
"""

from django.conf import settings


def static_version(request):
    """给模板注入 `static_version`，用于 JS/CSS 缓存刷新。"""
    return {"static_version": settings.STATIC_VERSION}
