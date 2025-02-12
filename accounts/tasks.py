from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task
def send_async_email_to_user(user_email, code):
    email = send_mail(
        'verification code',
        str(code),
        settings.FROM_EMAIL,
        [user_email]
    )

    print('email sent to: ', user_email, 'code is:', code)
    return email
