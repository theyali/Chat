from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<pk>\d+)/$', consumers.GameConsumer.as_asgi()),
]
