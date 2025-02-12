from random import randint

from django.db import models
from django.core.cache import cache

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager

class CustomUser(AbstractUser):
    email = models.EmailField(verbose_name=_('Email Address'), unique=True)
    username = models.CharField(verbose_name=_('User Name'), max_length=50, unique=True)
    bio = models.TextField(verbose_name=_('Biography'), max_length=250, blank=True, null=True)
    avatar = models.ImageField(verbose_name=_('Profile Avatar'), upload_to='profile_avatars', blank=True, null=True)
    is_active = models.BooleanField(verbose_name=_('Is Active'), default=True)
    is_admin = models.BooleanField(verbose_name=_('Is Admin'), default=False)
    verified = models.BooleanField(verbose_name=_('Is Verified'), default=False)
    is_premium = models.BooleanField(verbose_name=_('Is Premium'), default=False)

    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', )

    objects = CustomUserManager()

    def generate_otp_code(self):
        if self.verified:
            return None

        otp_code = randint(100000, 999999)
        cache.set(f'user_otp_{self.id}', otp_code, timeout=60*5) # 5 minutes
        return otp_code
    
    def validate_verification_code(self, code):
        cache_key = f'user_otp_{self.id}'
        otp_code =  cache.get(cache_key)
        if otp_code and str(otp_code) == str(code):
            self.verified = True
            self.save()
            cache.delete(cache_key)
            return True
        return False

    def __str__(self):
        return f'username: {self.username} - email: {self.email}'
    