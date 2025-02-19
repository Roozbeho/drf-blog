from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification

def send_notification(user_id, message):
    channel_layer = get_channel_layer()
    Notification.objects.create(user_id=user_id, message=message)
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user_id}',
        {
            'type': 'send_notification_event',
            'message': message
        }
    )
