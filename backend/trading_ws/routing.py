"""WebSocket URL routing for real-time trading data."""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Live agent signal decisions — group: signals_{pair}
    re_path(r"^ws/signals/(?P<pair>[A-Z]{6})/$", consumers.SignalConsumer.as_asgi()),
    # Live price ticks — group: prices_{pair}
    re_path(r"^ws/prices/(?P<pair>[A-Z]{6})/$", consumers.PriceConsumer.as_asgi()),
]
