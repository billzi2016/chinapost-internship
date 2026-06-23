from django.urls import path

from apps.web.views import chat_page


urlpatterns = [
    path("", chat_page, name="chat"),
]
