"""Web 页面 URL。

当前 Web 端只有一个聊天主页面，所有动态交互走 `/api/`。
"""

from django.urls import path

from apps.web.views import chat_page


urlpatterns = [
    path("", chat_page, name="chat"),
]
