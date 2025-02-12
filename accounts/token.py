from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.cache import cache
from rest_framework.exceptions import AuthenticationFailed

class RedisBlackListMixin:
    def is_token_blackedlisted(self, token):
        return True if cache.get(token) else False
    
    def blacklist_token(self, token):
        cache.set(token, 'blacked_list', timeout=60*60*24*7) # 7 days

class CustomJWTAuthenticationClass(JWTAuthentication, RedisBlackListMixin):
    def authenticate(self, request):
        try:
            user = super().authenticate(request)
            if user:
                if self.is_token_blackedlisted(user[1]):
                    raise AuthenticationFailed('Token is blocked')
                return user
        except AuthenticationFailed as e:
            raise e
        except Exception as e:
            raise e
        return None