from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import GenericAPIView, ListAPIView

from .models import Notification
from .serializers import NotificationSerializer

class NotificatoinsApiView(ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def change_notification_state(self):
        self.get_queryset().update(is_read=True)
    
    def get(self, request, *args, **kwargs):
        self.change_notification_state()
        return self.list(request, *args, **kwargs)
            