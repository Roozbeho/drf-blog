from rest_framework import serializers

from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', read_only=True)
    class Meta:
        model = Notification
        fields = ['user', 'message', 'creation_time']