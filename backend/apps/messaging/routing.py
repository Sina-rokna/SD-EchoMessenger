from django.urls import path

from .consumers import SpaceConsumer

websocket_urlpatterns = [
    path("ws/spaces/<uuid:space_id>/", SpaceConsumer.as_asgi()),
]
