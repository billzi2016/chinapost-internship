"""Web 页面视图。

这里只负责渲染模板和提供初始页面数据；聊天、RAG、SFT 和工单等交互都通过前端 JS 调用 API 完成。
"""

from django.shortcuts import render

from apps.core.models import Conversation


def chat_page(request):
    """渲染聊天主页面。

    初始只加载最近 30 个会话，避免历史会话很多时首屏渲染过慢。
    """
    return render(
        request,
        "web/chat.html",
        {"conversations": Conversation.objects.all()[:30]},
    )
