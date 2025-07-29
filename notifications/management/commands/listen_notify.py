from django.core.management.base import BaseCommand
import asyncio
from notifications.listener import listen_forever


class Command(BaseCommand):
    def handle(self, *args, **opts):
        asyncio.run(listen_forever())
