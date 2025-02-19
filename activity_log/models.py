from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class ActivityLog(models.Model):
    class Activity_Type(models.TextChoices):
        CREATE = 'CREATE', 'Create'
        READ = 'READ', 'Read'
        UPDATE = 'UPDATE', 'Update',
        DELETE = 'DELETE', 'Delete',
        LOGIN = 'LOGIN', 'Login',
        LOGOUT = 'LOGOUT', 'Logout',
        LOGIN_FAILED = 'LOGIN_FAIL', 'Login Failed',
        LIKE = 'LIKE', 'Like',
        UNLIKE = 'UN_LIKE', 'Un Like',
        FOLLOW = 'FOLLOW', 'Follow'
        UNFOLLOW = 'UN_FOLLOW', 'Un Follow'
        BOOKMARK = 'BOOKMARK', 'Bookmark'
        UNBOOKMARK = 'UN_BOOKMARK', 'Un bookmark'

    class Action_Status(models.TextChoices):
        SUCCESS = 'SUCC', 'Success'
        FAILED = 'FAIL', 'Failed'

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='activities')
    action_type = models.CharField(choices=Activity_Type.choices, max_length=20)
    action_time = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)
    status = models.CharField(choices=Action_Status.choices, max_length=10, blank=True, null=True)
    data = models.JSONField(default=dict, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        indexes = [
            models.Index(fields=('user', )),
            models.Index(fields=('action_type', ))
        ]

        ordering = ('-action_time', )

    def __str__(self):
        user = self.user.username if self.user else 'Unknown User'
        return f'{self.action_type} by {user} on {self.action_time}'