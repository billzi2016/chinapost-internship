from django.shortcuts import render

from apps.core.models import Conversation


def chat_page(request):
    return render(
        request,
        "web/chat.html",
        {"conversations": Conversation.objects.all()[:30]},
    )
