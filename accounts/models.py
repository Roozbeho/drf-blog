from random import randint
from hashlib import sha256

from django.db import models
from django.core.cache import cache

from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager

class Permission:
    FOLLOW = 1
    LIKE = 2
    BOOKMARK = 4
    COMMENT = 8
    WRITE = 16
    EDIT_ARTICLE = 32
    DELETE_ARTICLE = 64
    MODERATE_COMMENTS = 128
    ADMIN = 256

    @classmethod
    def get_name(cls, val):
        return {value:key \
                for key, value in dict(vars(Permission)).items() if isinstance(value, int)
            }.get(val, None)

class Role(models.Model):
    name = models.CharField(unique=True, max_length=100)
    default = models.BooleanField(default=False)
    permissions = models.IntegerField(default=0)

    @classmethod
    def insert_roles(cls):
        roles = {
            'User': [Permission.LIKE, Permission.COMMENT],  # Basic users
            'PremiumUser': [Permission.FOLLOW, Permission.LIKE, Permission.BOOKMARK,
                            Permission.COMMENT, Permission.WRITE],  # Writers
            'Moderator': [Permission.MODERATE_COMMENTS, Permission.COMMENT,
                         Permission.EDIT_ARTICLE, Permission.DELETE_ARTICLE],  # Content Moderators
            'Administrator': [Permission.ADMIN, Permission.FOLLOW, Permission.LIKE, 
                              Permission.BOOKMARK, Permission.COMMENT],  # Manages users
        }
        default_role = 'User'
        for role_name, perms in roles.items():
            role = cls.objects.filter(name=role_name)

            if not role.exists():
                role = cls.objects.create(name=role_name, default = (role_name == default_role))
            else:
                role = role.first()

            role.reset_permission()
            for perm in perms:
                role.add_permission(perm)

            role.save()

    @classmethod
    def get_default_role_pk(cls):
        role, created = cls.objects.get_or_create(
            name='User', defaults={'permissions': Permission.LIKE | Permission.COMMENT}
        )
        return role.pk

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm
    
    def reset_permission(self):
        self.permissions = 0
    
    def has_permission(self, perm):
        return (self.permissions & perm) == perm
    
    def __str__(self):
        return f'{self.name} (permissions: {self.permissions})'
      
class CustomUser(AbstractUser):
    email = models.EmailField(verbose_name=_('Email Address'), unique=True)
    username = models.CharField(verbose_name=_('User Name'), max_length=50, unique=True)
    bio = models.TextField(verbose_name=_('Biography'), max_length=250, blank=True, null=True)
    avatar = models.ImageField(verbose_name=_('Profile Avatar'), upload_to='profile_avatars', blank=True, null=True)
    is_active = models.BooleanField(verbose_name=_('Is Active'), default=True)
    is_admin = models.BooleanField(verbose_name=_('Is Admin'), default=False)
    verified = models.BooleanField(verbose_name=_('Is Verified'), default=False)
    is_premium = models.BooleanField(verbose_name=_('Is Premium'), default=False)
    role = models.ForeignKey(Role, default=Role.get_default_role_pk, null=True,
                             on_delete=models.SET_NULL, related_name='users')

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
    