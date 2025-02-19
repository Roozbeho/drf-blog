import json
from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from django.http import Http404
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('request_user', AnonymousUser())

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        self.group_name = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()


    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name,self.channel_name)


    async def send_notification_event(self, event):
        message = event.get('message', '')
        await self.send(text_data=json.dumps({'message': message}))


