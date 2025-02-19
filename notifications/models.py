from django.db import models
from django.contrib.auth import get_user_model

class Notification(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False, blank=True)
    creation_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-creation_time', )

    def __str__(self):
        return f'Notification for {self.user.username}'
    