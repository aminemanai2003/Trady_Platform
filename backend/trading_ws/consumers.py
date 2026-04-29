"""
WebSocket Consumers for real-time trading updates.

SignalConsumer  — streams agent pipeline decisions (BUY/SELL/REJECTED + XAI)
PriceConsumer   — streams live price ticks from InfluxDB

Groups:
    signals_{pair}  — broadcast when MasterSignalView generates a decision
    prices_{pair}   — broadcast by the periodic price broadcaster task
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class SignalConsumer(AsyncWebsocketConsumer):
    """
    Real-time agent signal stream.

    Connect:  ws://host/ws/signals/EURUSD/
    Receives: nothing (subscribe-only)
    Sends:    JSON pipeline result whenever MasterSignalView completes for this pair
    """

    async def connect(self):
        self.pair = self.scope["url_route"]["kwargs"]["pair"].upper()
        self.group_name = f"signals_{self.pair}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug(f"WS SignalConsumer connected: {self.pair}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Clients send nothing — this is a push-only feed
        pass

    # Called by channel layer when MasterSignalView broadcasts
    async def signal_update(self, event):
        await self.send(text_data=json.dumps({"type": "signal", "data": event["data"]}))


class PriceConsumer(AsyncWebsocketConsumer):
    """
    Real-time price tick stream.

    Connect:  ws://host/ws/prices/EURUSD/
    Sends:    JSON price tick every ~5 s from price_broadcaster task
    """

    async def connect(self):
        self.pair = self.scope["url_route"]["kwargs"]["pair"].upper()
        self.group_name = f"prices_{self.pair}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.debug(f"WS PriceConsumer connected: {self.pair}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        pass

    # Called by channel layer when price_broadcaster sends a tick
    async def price_tick(self, event):
        await self.send(text_data=json.dumps({"type": "price", "data": event["data"]}))
