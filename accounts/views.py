from django.shortcuts import render
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import UserRateThrottle
from rest_framework.decorators import action

from .models import CustomUser, Follow
from . import serializers
from .utils import generate_tokens_for_user
from .permissions import NotAuthenticatedUserOnly, NotVerifiedAccountOnly, VerifiedAccountOnly
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
    
class ChangePasswordApiView(GenericAPIView):
    permission_classes = (IsAuthenticated, VerifiedAccountOnly)
    authentication_classes = (CustomJWTAuthenticationClass, )
    serializer_class = serializers.ChangePasswordSerializer

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: CustomUser = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        if not user.check_password(old_password):
            return Response({'error': 'Old password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        if old_password == new_password:
            return Response({'error': 'New password cannot be the same as the old password'}, status=status.HTTP_400_BAD_REQUEST)
            
        user.set_password(new_password)
        user.save()
        return Response({'success': 'Password chnged successfully'}, status=status.HTTP_200_OK)
    

class FollowApiView(viewsets.ViewSet, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = 'username'
    lookup_url_kwarg = 'username'
    

    def _get_user(self, username):
        return get_object_or_404(CustomUser, username=username)
    
    @action(methods=['POST'], detail=True, url_path='toggle_follow')
    def toggle_follow(self, request, username=None):
        followed_user = self._get_user(username)
        follower_user = request.user

        if followed_user == follower_user:
            return Response({'error': "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        follow_obj, created = Follow.objects.get_or_create(follower=follower_user, followed=followed_user)
        if not created:
            follow_obj.delete()
            return Response({'success': 'You have unfollowed this user.'}, status=status.HTTP_200_OK)

        return Response({'success': 'You are now following this user.'}, status=status.HTTP_201_CREATED)

    def _get_follow_list(self, query_param, serializer_class):
        follow_list = Follow.objects.filter(**{query_param: self.request.user})
        serializer = serializer_class(follow_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['GET'], detail=False, url_path='followers', url_name='followers-list')
    def followers_list(self, request):
        return self._get_follow_list('followed', serializers.FollowerListSerializer)

    @action(methods=['GET'], detail=False, url_path='following', url_name='following-list')
    def following_list(self, request):
        return self._get_follow_list('follower', serializers.FollowingListSerializer)