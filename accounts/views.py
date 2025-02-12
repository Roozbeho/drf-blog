from django.shortcuts import render
from django.core.cache import cache

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import UserRateThrottle

from .models import CustomUser
from . import serializers
from .utils import generate_tokens_for_user
from .permissions import NotAuthenticatedUserOnly, NotVerifiedAccountOnly
from .token import CustomJWTAuthenticationClass
from .tasks import send_async_email_to_user

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
    
class OTPRequestThrottle(UserRateThrottle):
    rate = '3/minute'

class AccountVerificationApiView(APIView):
    permission_classes = (IsAuthenticated, NotVerifiedAccountOnly)
    authentication_classes = (CustomJWTAuthenticationClass, )
    throttle_classes = (OTPRequestThrottle, )

    def get(self, request):
        user: CustomUser = request.user
        cache_key = f'user_otp_{user.id}'

        if cache.get(cache_key):
            return Response({'error': 'OTP already sent. please wait'}, status=status.HTTP_400_BAD_REQUEST)

        otp_code = user.generate_otp_code()
        if otp_code:
            send_async_email_to_user.delay(user.email, otp_code)
            return Response({'success': 'OTP sent to your email'}, status=status.HTTP_200_OK)
        
        return Response({'error': 'something went wrong'}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        serializer = serializers.OtpCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_code = serializer.validated_data.get('otpcode')

        user: CustomUser = request.user
        if user.validate_verification_code(otp_code):
            return Response({'success': 'Your account has been verified'}, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)