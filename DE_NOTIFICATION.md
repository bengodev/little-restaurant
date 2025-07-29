🎉  Real-time Database update notification in Django app with `Redis`, `Websocket`, `channels[daphne]`,  

The Redis layer is what let the listener and the consumer talk to each other.  

**Basic steps:**

- PostgreSQL trigger → NOTIFY  
- `listen_notify` command → Redis broadcast  
- Daphne + consumer → WebSocket push  
- Browser → instant console log & sound

Keep Redis running and both processes (Daphne and the listener) supervised.


### [End-to-end checklist - click here](#steps)
### [For Multiple Tables - click here](#multi)

## 1. PostgreSQL trigger

*Run this command in `psql` terminal*

```bash
# Structure
CREATE OR REPLACE FUNCTION notify_on_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'my_table_events', // (optional) Could change Events name (unique per event)
        json_build_object(
            'op',   TG_OP,
            'data', row_to_json(NEW)
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_my_table_notify  // (optional) trg_(any_name)_notify
AFTER INSERT OR UPDATE ON my_table // Replace my_table with your table name
FOR EACH ROW
EXECUTE FUNCTION notify_on_change();

# Example

CREATE OR REPLACE FUNCTION notify_on_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'human_detection_events',
        json_build_object(
            'op',   TG_OP,
            'data', row_to_json(NEW)
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_human_detection_notify
AFTER INSERT OR UPDATE ON violation_humandetections
FOR EACH ROW
EXECUTE FUNCTION notify_on_change();

```

Below are the only places you need to edit in the two SQL blocks, and what you should put there.

1. Channel name (the string passed to `pg_notify`)  
   `'my_table_events'`  
   → Pick any short, unique name you like (letters, digits, underscore).  
   Example: `'orders_channel'`, `'user_notifications'`

2. Trigger table name  
   `my_table`  
   → Replace with the actual table you want to watch.  
   Example: `orders`, `users`, `inventory`

3. (Optional) Trigger timing  
   `AFTER INSERT OR UPDATE`  
   If you only want INSERTs, change to:  
   `AFTER INSERT`  
   If you also want DELETEs, make it:  
   `AFTER INSERT OR UPDATE OR DELETE`

4. (Optional) Trigger name  
   `trg_my_table_notify`  
   → Name can be anything, just keep it unique per table.  
   Example: `trg_orders_notify`, `trg_users_notify`

Nothing else in the snippet has to change.

## 2. Django listener (async task)

*Install deps:*

```bash
pip3 install 'psycopg[binary]>=3'
```

*Create `notifications/listener.py` (anywhere on your Python path):*

```bash
import asyncio, json, os
import psycopg
from django.conf import settings

dsn = settings.DATABASES["default"]
connection_string = (
    f"dbname={dsn['NAME']} user={dsn['USER']} password={dsn['PASSWORD']} "
    f"host={dsn['HOST']} port={dsn.get('PORT', 5432)}"
)

async def listen_forever():
    async with await psycopg.AsyncConnection.connect(
        connection_string, autocommit=True
    ) as aconn:
        async with aconn.cursor() as cur:
            await cur.execute("LISTEN my_table_events")
            async for notify in aconn.notifies():
                payload = json.loads(notify.payload)
                # push to WebSocket group, SSE, or Celery task
                await broadcast_to_clients(payload)

async def broadcast_to_clients(payload):
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    await channel_layer.group_send(
        "global", {"type": "table.change", "payload": payload}
    )

if __name__ == "__main__":
    asyncio.run(listen_forever())
```


Include `notifications` in INSTALLED_APP:

```bash
INSTALLED_APPS = [
    ...
    'notifications',
    ...
]
```
**add `notifications/__init__.py`**


Only three things need to match the rest of your project:

1. Channel name inside `LISTEN …`  
   `"LISTEN human_detection_events"` → must be **identical** to the string you used in the trigger’s `pg_notify()` (case-sensitive).

2. WebSocket / Channel layer group name  
   `"global"` → change only if your WebSocket consumers use a different group or room name.  
   If you leave it as `"global"`, make sure your consumer does  
   ```python
   await self.channel_layer.group_add("global", self.channel_name)
   ```

3. Consumer event type  
   `"table.change"` → must match the method name in your consumer (`async def table_change(self, event):`).  
   If you prefer something more specific you can rename both places, e.g. `"human.detection"`.

Everything else (DSN, psycopg usage, asyncio loop, etc.) stays exactly as shown.


**Start the listener in a separate terminal or supervisor:**

```bash
# python3 manage.py shell -c "import notifications.listener; notifications.listener.listen_forever()"

python3 manage.py shell -c "import asyncio, notifications.listener; asyncio.run(notifications.listener.listen_forever())"

```

## 3. Django-Channels consumer

*Install deps `channels`:*

```bash
pip3 install channels
```

Include `channels` in INSTALLED_APP:

```bash
INSTALLED_APPS = [
    ...
    'channels',
    ...
]
```

`notifications/consumers.py`

```bash
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("global", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("global", self.channel_name)

    async def table_change(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
```

Wire it up in `routing.py`, mount with Daphne/Uvicorn.


### Here is a minimal, step-by-step checklist.  
It explains:

1. Where the `routing.py` file comes from.  
2. How to “wire up” the consumer.  
3. How to “mount with Daphne/uvicorn” (i.e. run the ASGI server instead of the default WSGI one).

────────────────────────────────────
1. Create / check the folder layout
────────────────────────────────────
yourproject/
├── manage.py
├── yourproject/        (the Django settings package)
│   ├── __init__.py
│   ├── asgi.py         ← we will touch this
│   ├── settings.py
│   └── …               (urls.py, wsgi.py, …)
└── notifications/
    ├── __init__.py
    ├── consumers.py    ← already exists
    └── routing.py      ← ADD this (new file)

────────────────────────────────────
2. notifications/routing.py  (new file)
────────────────────────────────────
```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ws://<host>/ws/table/
    re_path(r'^ws/table/$', consumers.TableConsumer.as_asgi()),
]
```

────────────────────────────────────
3. yourproject/asgi.py  (edit or create)
────────────────────────────────────
Django ≥ 3.0 already ships an `asgi.py`.  
Replace its contents with:

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import notifications.routing   # our file above

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "yourproject.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),          # normal HTTP/REST
    "websocket": AuthMiddlewareStack(        # WebSocket support
        URLRouter(
            notifications.routing.websocket_urlpatterns
        )
    ),
})
```

────────────────────────────────────
4. Settings tweaks
────────────────────────────────────
a) Install Channels:

```bash
pip3 install 'channels[daphne]'   # or uvicorn[standard]
```

b) Add the Channels layer and app:

**Make sure to add `daphne` before `django.contrib.staticfiles` in INSTALLED_APPS=[]** 

```python
# settings.py
INSTALLED_APPS = [
    'daphne',               # or 'channels' if you use uvicorn
    'django.contrib.admin',
    'django.contrib.auth',
    ...
    'notifications',
]

# Use Redis instead
# Channels back-end (in-memory for dev, Redis for prod)
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}
```
*For production:* Install the companion package (only once):

```bash
pip install channels-redis
```

*For production:* Replace the in-memory backend with the Redis layer:

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": ["redis://127.0.0.1:6379/0"],   # or ["redis://password@host:port/db"]
        },
    },
}
```



────────────────────────────────────
5. Run the ASGI server
────────────────────────────────────
Option A – Daphne (comes with `channels[daphne]`):

```bash
daphne -b 0.0.0.0 -p 8000 yourproject.asgi:application
```

Option B – Uvicorn:

```bash
uvicorn yourproject.asgi:application --host 0.0.0.0 --port 8000 --reload
```

Now:

- Any HTTP request → handled by Django views.  
- WebSocket connection to `ws://localhost:8000/ws/table/` → handled by `TableConsumer`.

That is what “mount with Daphne/Uvicorn” means – 

#### Now start the ASGI server instead of the classic `python3 manage.py runserver`.


## 4. Front-end (plays a sound)

add websocket connection script in `base.html` template.
*Cautions:* Do not enclose the script withing template block i.e. {%%}, use directly within `<head>` section.

```js
<script>
    const ws = new WebSocket(`ws://${window.location.host}/ws/table/`);
    ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        console.log("new row:", msg.data);
        new Audio("/static/ping.mp3").play();
    };
<script>
```

## Keep in Mind

- Use Redis, local inMemory settings doesn't work properly
- Every time assets changes you need to restart `daphne core.asgi:application -b 0.0.0.0 -p 8000` 
- Websocket connected when app open in Browser and to reload if `daphne` terminal restart 



## (Repeat)

## <a name="steps"></a> End-to-end checklist – every single step in order

1. PostgreSQL table  
   `violation_humandetections` (camera_id, violation_date, …)

2. PostgreSQL trigger + function  
   Run once in psql:

```sql
CREATE OR REPLACE FUNCTION notify_on_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'human_detection_events',
        json_build_object(
            'op',   TG_OP,
            'data', row_to_json(NEW)
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_humandetections_notify
AFTER INSERT ON violation_humandetections
FOR EACH ROW EXECUTE FUNCTION notify_on_change();
```

3. Install Python packages

```bash
pip3 install "channels[daphne]" channels-redis psycopg[binary]
```

4. Django settings (settings.py)

```python
INSTALLED_APPS = [
    'daphne',          # ASGI server
    'django.contrib.admin',
    ...
    'notifications',   # your app
]

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": ["redis://127.0.0.1:6379/0"]},
    },
}
```

5. ASGI entry-point (core/asgi.py)

```python
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import notifications.routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(notifications.routing.websocket_urlpatterns)
    ),
})
```

6. WebSocket consumer (notifications/consumers.py)

```python
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class TableConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("global", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("global", self.channel_name)

    async def table_change(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
```

7. WebSocket routing (notifications/routing.py)

```python
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/table/$', consumers.TableConsumer.as_asgi()),
]
```

8. Listener management command  
notifications/management/commands/listen_notify.py

```python
from django.core.management.base import BaseCommand
import asyncio
from notifications.listener import listen_forever

class Command(BaseCommand):
    def handle(self, *args, **opts):
        asyncio.run(listen_forever())
```

notifications/listener.py

```python
import asyncio, json, psycopg
from django.conf import settings
from channels.layers import get_channel_layer

dsn = settings.DATABASES["default"]
conn_str = (
    f"dbname={dsn['NAME']} user={dsn['USER']} password={dsn['PASSWORD']} "
    f"host={dsn['HOST']} port={dsn.get('PORT', 5432)}"
)

async def listen_forever():
    async with await psycopg.AsyncConnection.connect(conn_str, autocommit=True) as aconn:
        await aconn.execute("LISTEN human_detection_events")
        async for notify in aconn.notifies():
            payload = json.loads(notify.payload)
            await broadcast_to_clients(payload)

async def broadcast_to_clients(payload):
    channel_layer = get_channel_layer()
    await channel_layer.group_send("global", {"type": "table.change", "payload": payload})
```

9. Static file  
Place `audio.wav` in `notifications/static/audio.wav` and run:

```bash
python3 manage.py collectstatic --no-input
```

10. Template snippet (change_list.html or base template)

```html
{% load static %}
<script>
const ws = new WebSocket(`ws://${window.location.host}/ws/table/`);
ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    console.log("new row:", msg.data);
    new Audio("{% static 'audio.wav' %}").play();
};
</script>
```

11. Start services

```bash
# 1. Redis
redis-server          # or brew services start redis

# 2. ASGI server
daphne core.asgi:application -b 0.0.0.0 -p 8000

# 3. Listener
python3 manage.py listen_notify
```

12. Test  
Insert a row:

```sql
INSERT INTO violation_humandetections(camera_id, violation_date, violation_time, violation_image)
VALUES(2, '2025-07-28', '15:00:00', '/media/…');
```

Flow:

PostgreSQL trigger → NOTIFY  
→ listener receives → Redis broadcast  
→ WebSocket consumer → browser  
→ console log + sound plays instantly.


Structured process to extend the current single-table setup to **three** tables
(violation_humandetections, violation_lotodetections, violation_ppedetections)
without duplicating code.

## <a name="multi"></a>For Multiple tables

────────────────────────────────────────
1.  Decide how many **channels** you want
────────────────────────────────────────
A.  One **global** channel  
    Every table emits the same JSON structure, and the front-end figures out the table from the payload.  
    → 1 trigger per table → 1 listener → 1 consumer → 1 WebSocket URL.

B.  One **channel per table**  
    Each table has its own `pg_notify('humans', …)` / `pg_notify('loto', …)` / `pg_notify('ppe', …)`  
    → 3 triggers → 1 or 3 listeners → 3 WebSocket endpoints (or a single multiplexed one).

For a dashboard that shows all violations together, **option A** (single channel) is simpler.

────────────────────────────────────────
2.  Re-usable trigger function (option A)
────────────────────────────────────────
Create **one generic** trigger that receives the table name via TG_TABLE_NAME:

```sql
CREATE OR REPLACE FUNCTION notify_violation_change()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify(
        'violations_channel',
        json_build_object(
            'table', TG_TABLE_NAME,
            'op',    TG_OP,
            'data',  row_to_json(NEW)
        )::text
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

Attach it to the three tables:

```sql
CREATE TRIGGER trg_humans_notify
AFTER INSERT ON violation_humandetections
FOR EACH ROW EXECUTE FUNCTION notify_violation_change();

CREATE TRIGGER trg_loto_notify
AFTER INSERT ON violation_lotodetections
FOR EACH ROW EXECUTE FUNCTION notify_violation_change();

CREATE TRIGGER trg_ppe_notify
AFTER INSERT ON violation_ppedetections
FOR EACH ROW EXECUTE FUNCTION notify_violation_change();
```

────────────────────────────────────────
3.  Update the listener
────────────────────────────────────────
Change **only the channel name** in `listen_forever()`:

```python
await aconn.execute("LISTEN violations_channel")
```

Broadcast payload already contains `"table"` key, so nothing else changes.

────────────────────────────────────────
4.  Consumer stays the same
────────────────────────────────────────
No change—consumer just forwards the JSON; the browser can read `msg.table`.

────────────────────────────────────────
5.  Update routing.py path
────────────────────────────────────────
```bash
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ws://<host>/ws/table/
    re_path(r'^ws/violations/$', consumers.TableConsumer.as_asgi()),
]
```
────────────────────────────────────────
6.  Front-end (single WebSocket)
────────────────────────────────────────
```html
<script>
const ws = new WebSocket(`ws://${window.location.host}/ws/violations/`);
ws.onmessage = e => {
    const msg = JSON.parse(e.data);
    console.log(`Violation from ${msg.table}:`, msg.data);
    new Audio("{% static 'audio.wav' %}").play();
};
</script>
```

────────────────────────────────────────
7.  Optional – separate channels (option B)
────────────────────────────────────────
If you later want **separate sounds** or **separate widgets**, create three triggers:

```sql
CREATE TRIGGER trg_humans_notify
AFTER INSERT ON violation_humandetections
FOR EACH ROW EXECUTE FUNCTION pg_notify('humans_channel', json_build_object(...));

CREATE TRIGGER trg_loto_notify
AFTER INSERT ON violation_lotodetections
FOR EACH ROW EXECUTE FUNCTION pg_notify('loto_channel', json_build_object(...));

CREATE TRIGGER trg_ppe_notify
AFTER INSERT ON violation_ppedetections
FOR EACH ROW EXECUTE FUNCTION pg_notify('ppe_channel', json_build_object(...));
```

Then:

- one listener that issues  
  `LISTEN humans_channel; LISTEN loto_channel; LISTEN ppe_channel;`  
  and broadcasts to **three different groups** (`"humans"`, `"loto"`, `"ppe"`).

- three consumers (or one parameterized consumer) mounted on  
  `/ws/humans/`, `/ws/loto/`, `/ws/ppe/`.

────────────────────────────────────────
Summary of minimal steps
────────────────────────────────────────
1. Create generic trigger, attach to 3 tables.  
2. Change listener to `LISTEN violations_channel`.  
3. Keep existing consumer and WebSocket URL.  
4. Browser payload now tells you which table the violation came from.