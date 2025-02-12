from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from . import serializers
from .utils import generate_tokens_for_user
from .permissions import NotAuthenticatedUserOnly
from .token import CustomJWTAuthenticationClass

class LoginApiView(APIView):
    permission_classes = (NotAuthenticatedUserOnly, )
    authentication_classes = (CustomJWTAuthenticationClass, )

    def post(self, request):
        serializer = serializers.UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        customuser_serializer = serializers.CustomUserSerializer(user)

        data = customuser_serializer.data
        data.pop('id')
        token = RefreshToken.for_user(user)
        data['token'] = {"refresh": str(token), "access": str(token.access_token)}
        
        return Response(data, status=status.HTTP_200_OK)
    
class LogoutApiView(APIView):
    permission_classes = (IsAuthenticated, )
    authentication_classes = (CustomJWTAuthenticationClass, )
    def post(self, request):
        try:
            access_token = request.headers.get('Authorization').split(' ')[1]
            CustomJWTAuthenticationClass().blacklist_token(access_token)
            return Response({'success': 'logged out'}, status=status.HTTP_200_OK)
        except Exception as e:
            raise Response({'error': 'Invalid or expired token'}, status=status.HTTP_401_UNAUTHORIZED)
        
class RegistrationApiView(APIView):
    permission_classes = (NotAuthenticatedUserOnly, )

    def post(self, request):
        serializer = serializers.RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        return Response({'success': 'registered successfully'}, status=status.HTTP_201_CREATED)