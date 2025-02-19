from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.tokens import AccessToken
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.authentication import JWTAuthentication

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope.setdefault('request_user', AnonymousUser())

        token = self.get_token_from_scope(scope)
        if token:
            user = await self.get_user_from_token(token)
            scope['request_user'] = user

        return await super().__call__(scope, receive, send)
    
    def get_token_from_scope(self, scope):
        headers = dict(scope.get('headers', []))
        auth_header = headers.get(b'authorization', b'').decode('utf-8')

        if auth_header.startswith("Bearer "):
            return auth_header.split(" ", 1)[1]
        
        return auth_header if auth_header else None
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            jwt_auth = JWTAuthentication()
            validated_token = jwt_auth.get_validated_token(token)
            return jwt_auth.get_user(validated_token)
        except:
            return AnonymousUser()