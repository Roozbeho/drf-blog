from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.urls import resolve
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from activity_log.mixins import ActivityLogMixin
from activity_log.models import ActivityLog
from notifications.utils import send_notification

from . import serializers
from .models import CustomUser, Follow, Permission
from .permissions import NotAuthenticatedUserOnly, NotVerifiedAccountOnly, VerifiedAccountOnly
from .tasks import send_async_email_to_user
from .token import CustomJWTAuthenticationClass


class LoginApiView(APIView):
    permission_classes = (NotAuthenticatedUserOnly,)
    authentication_classes = (CustomJWTAuthenticationClass,)

    def post(self, request):
        serializer = serializers.UserLoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        customuser_serializer = serializers.CustomUserSerializer(user)

        data = customuser_serializer.data
        data.pop("id")
        token = RefreshToken.for_user(user)

        user_logged_in.send(user.__class__, request=request, user=user)

        data["token"] = {"refresh": str(token), "access": str(token.access_token)}

        return Response(data, status=status.HTTP_200_OK)


class LogoutApiView(APIView):
    permission_classes = (IsAuthenticated,)
    authentication_classes = (CustomJWTAuthenticationClass,)

    def post(self, request):
        try:
            access_token = request.headers.get("Authorization").split(" ")[1]
            CustomJWTAuthenticationClass().blacklist_token(access_token)

            user_logged_out.send(request.user.__class__, request=request, user=request.user)

            return Response({"success": "logged out"}, status=status.HTTP_200_OK)
        except Exception as e:
            raise Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)


class RegistrationApiView(ActivityLogMixin, APIView):
    permission_classes = (NotAuthenticatedUserOnly,)

    def post(self, request):
        serializer = serializers.RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        return Response({"success": "registered successfully"}, status=status.HTTP_201_CREATED)

    def _build_log_message(self, request):
        return f"User: {self._get_user_mixin(request)} \
            -- Action Type: {'Sign up to Website'} \
            -- Path: {request.path} \
            -- Path Name: {resolve(request.path_info).url_name}"


class OTPRequestThrottle(UserRateThrottle):
    rate = "3/minute"


class AccountVerificationApiView(ActivityLogMixin, APIView):
    permission_classes = (IsAuthenticated, NotVerifiedAccountOnly)
    authentication_classes = (CustomJWTAuthenticationClass,)
    throttle_classes = (OTPRequestThrottle,)

    def get(self, request):
        user: CustomUser = request.user
        cache_key = f"user_otp_{user.id}"

        if cache.get(cache_key):
            return Response({"error": "OTP already sent. please wait"}, status=status.HTTP_400_BAD_REQUEST)

        otp_code = user.generate_otp_code()
        if otp_code:
            send_async_email_to_user.delay(user.email, otp_code)
            return Response({"success": "OTP sent to your email"}, status=status.HTTP_200_OK)

        return Response({"error": "something went wrong"}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        serializer = serializers.OtpCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_code = serializer.validated_data.get("otpcode")

        user: CustomUser = request.user
        if user.validate_verification_code(otp_code):
            return Response({"success": "Your account has been verified"}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

    def _build_log_message(self, request):
        return f"User: {self._get_user_mixin(request)} \
            -- Action Type: {
                    'Activate Account' 
                    if request.action == 'get'
                    else 'Request OTP Code To Activate Account'
                        } \
            -- Path: {request.path} \
            -- Path Name: {resolve(request.path_info).url_name}"


class ChangePasswordApiView(ActivityLogMixin, GenericAPIView):
    permission_classes = (IsAuthenticated, VerifiedAccountOnly)
    authentication_classes = (CustomJWTAuthenticationClass,)
    serializer_class = serializers.ChangePasswordSerializer

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user: CustomUser = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        if old_password == new_password:
            return Response(
                {"error": "New password cannot be the same as the old password"}, status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()
        return Response({"success": "Password chnged successfully"}, status=status.HTTP_200_OK)

    def _build_log_message(self, request):
        if self.action == "put":
            return f"User: {self._get_user_mixin(request)} \
                -- Action Type: {'Change Password'} \
                -- Path: {request.path} \
                -- Path Name: {resolve(request.path_info).url_name}"
        return super()._build_log_message(request)


class FollowApiView(ActivityLogMixin, viewsets.ViewSet, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_field = "username"
    lookup_url_kwarg = "username"
    FOLLOWING = False

    def _get_user(self, username):
        return get_object_or_404(CustomUser, username=username)

    @action(methods=["POST"], detail=True, url_path="toggle_follow")
    def toggle_follow(self, request, username=None):
        followed_user = self._get_user(username)
        follower_user = request.user

        if followed_user == follower_user:
            return Response({"error": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        self.follow_obj, created = Follow.objects.get_or_create(follower=follower_user, followed=followed_user)
        if not created:
            self.FOLLOWING = False
            self.unfollowed_user = self.follow_obj.followed.username
            self.follow_obj.delete()
            self._send_message_to_notifiaction(request.user, followed_user, self.FOLLOWING)

            return Response({"success": "You have unfollowed this user."}, status=status.HTTP_200_OK)
        self.FOLLOWING = True
        self._send_message_to_notifiaction(request.user, followed_user, self.FOLLOWING)

        return Response({"success": "You are now following this user."}, status=status.HTTP_201_CREATED)

    def _get_follow_list(self, query_param, serializer_class):
        follow_list = Follow.objects.filter(**{query_param: self.request.user})
        serializer = serializer_class(follow_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=False, url_path="followers", url_name="followers-list")
    def followers_list(self, request):
        return self._get_follow_list("followed", serializers.FollowerListSerializer)

    @action(methods=["GET"], detail=False, url_path="following", url_name="following-list")
    def following_list(self, request):
        return self._get_follow_list("follower", serializers.FollowingListSerializer)

    @staticmethod
    def _send_message_to_notifiaction(sendedr_user, receiver_user, action):
        notification_message = f'user {sendedr_user.username} {"Follow" if action else "Unfollow"} You.'
        notification_reviever_id = receiver_user.id
        send_notification(notification_reviever_id, notification_message)

    def _get_action_type(self, request):
        if self.action == "toggle_follow":
            if self.FOLLOWING:
                return ActivityLog.Activity_Type.FOLLOW
            return ActivityLog.Activity_Type.UNFOLLOW
        return super()._get_action_type(request)

    def _build_log_message(self, request):
        if self.action != "toggle_follow":
            return super()._build_log_message(request)

        return f"User: {self._get_user_mixin(request)} \
            -- Action Type: 'Following {self.follow_obj.follower.username}' \
                if self.FOLLOWING else \
                'Unfollow {self.unfollowed_user}' \
            -- Path: {request.path} \
            -- Path Name: {resolve(request.path_info).url_name}"


class UserProfileApiView(ActivityLogMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):

    def get_queryset(self):
        return CustomUser.objects.all()

    def get_object(self):
        return get_object_or_404(self.get_queryset(), username=self.kwargs.get("username"))

    def get_serializer_class(self, *args, **kwargs):
        user = self.request.user

        if self.get_object() == user or (user.is_authenticated and user.can(Permission.ADMIN)):
            return serializers.UserPrivateProfileSerializer
        return serializers.UserPublicProfileSeriallizer

    def retrieve(self, request, *args, **kwargs):
        user_obj = self.get_object()
        serializer = self.get_serializer(user_obj)
        print(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)
