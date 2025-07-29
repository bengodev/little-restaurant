import asyncio
import json
import os
import psycopg
from django.conf import settings

dsn = settings.DATABASES["default"]
connection_string = (
    f"dbname={dsn['NAME']} user={dsn['USER']} password={dsn['PASSWORD']} "
    f"host={dsn['HOST']} port={dsn.get('PORT', 5432)}"
)


async def broadcast_to_clients(payload):
    print('::::broadcast_to_clients:::')
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "global", {"type": "table.change", "payload": payload}
    )


async def listen_forever():
    print('::::listen_forever:::')
    async with await psycopg.AsyncConnection.connect(
        connection_string, autocommit=True
    ) as aconn:
        async with aconn.cursor() as cur:
            await cur.execute("LISTEN booking_channel")
            async for notify in aconn.notifies():
                payload = json.loads(notify.payload)
                # push to WebSocket group, SSE, or Celery task
                await broadcast_to_clients(payload)


if __name__ == "__main__":
    asyncio.run(listen_forever())
