from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_login_failed, user_logged_out
from django.conf import settings

from activity_log.models import ActivityLog
from .utils import get_client_ip

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    message = f"{user.username} is logged in with ip:{get_client_ip(request)}"
    ActivityLog.objects.create(user=user, action_type=ActivityLog.Activity_Type.LOGIN, remarks=message)


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    ip_address = 'Unknown' if not request else get_client_ip(request)
    message = f"Login Attempt Failed for email {credentials.get('email')} with ip: {ip_address}"
    ActivityLog.objects.create(action_type=ActivityLog.Activity_Type.LOGIN_FAILED, status=ActivityLog.Action_Status.FAILED,remarks=message)

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    message = f"{user.username} is logged out with ip:{get_client_ip(request)}"
    ActivityLog.objects.create(user=user, action_type=ActivityLog.Activity_Type.LOGOUT, remarks=message)