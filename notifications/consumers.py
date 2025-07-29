from channels.generic.websocket import AsyncWebsocketConsumer
import json


class TableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print('Websocket connected')
        await self.channel_layer.group_add("global", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("global", self.channel_name)

    async def table_change(self, event):
        print('Websocket table_change')
        await self.send(text_data=json.dumps(event["payload"]))
