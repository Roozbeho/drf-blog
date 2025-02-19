import re

from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.validators import UniqueValidator
from django.urls import reverse
from django.conf import settings
from urllib.parse import urlencode
from django.contrib.auth.signals import user_login_failed

from .models import CustomUser, Follow

class CustomUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'username', 'bio', 'avatar']
        # fields = '__all__'


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if not user or not user.is_active:

            user_login_failed.send(CustomUser, credentials=data, request=self.context['request'])
            
            raise serializers.ValidationError('Invalid email or password')
        return user
    
class RegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True,
                                   validators=[UniqueValidator(queryset=CustomUser.objects.all())])
    username = serializers.CharField(max_length=50,
                                     validators=[UniqueValidator(queryset=CustomUser.objects.all())])
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'username', 'password', 'confirm_password']

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'password': 'password fields didnt match'})
        return attrs
    
    def create(self, validated_data):
        user = CustomUser(email=validated_data['email'], username=validated_data['username'])
        user.set_password(validated_data['password'])
        user.save()
        
        return user
    
class OtpCodeSerializer(serializers.Serializer):
    otpcode = serializers.IntegerField(min_value=100000, max_value=9999999)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        if not re.match(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$', value):
            raise serializers.ValidationError('Minimum eight characters, at least one letter and one number')
        return value
    
class FollowerListSerializer(serializers.ModelSerializer):
    # follower = serializers.HyperlinkedIdentityField(view_name=)
    class Meta:
        model = Follow
        fields = ['follower']

class FollowingListSerializer(serializers.ModelSerializer):
    # followed = serializers.HyperlinkedIdentityField(view_name=)
    class Meta:
        model = Follow
        fields = ['followed']

class UserPublicProfileSeriallizer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    posts_that_write_by_user_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['username', 'bio', 'avatar', 'posts_that_write_by_user_url',]
    def get_avatar(self, obj):
        # TODO: set settings.DEFAULT_USER_AVATAR
        return obj.avatar.url if obj.avatar else None
    
    def get_posts_that_write_by_user_url(self, obj):
        return reverse('blog:post-list') +  "?" + urlencode({'search': obj.username})
class UserPrivateProfileSerializer(UserPublicProfileSeriallizer):
    activate = serializers.SerializerMethodField()
    premium = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    number_of_posts = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_that_write_by_user_url = serializers.SerializerMethodField()
    likes_posts_url = serializers.SerializerMethodField()
    follower_list_url = serializers.SerializerMethodField()
    following_list_url = serializers.SerializerMethodField()
    bookmarked_posts_list_url = serializers.SerializerMethodField() 

    class Meta(UserPublicProfileSeriallizer.Meta):
        fields = UserPublicProfileSeriallizer.Meta.fields + [
            'email', 'activate', 'premium', 'number_of_posts', 'followers_count', 'following_count',
            'follower_list_url', 'following_list_url', 'bookmarked_posts_list_url', 'likes_posts_url'
        ]

    def get_activate(self, obj):
        if obj.is_active:
            return True
        return reverse('auth:account-verify')
    
    def get_premium(self, obj):
        # TODO: Implement premium and point logic when required
        return obj.is_premium
    
    def get_avatar(self, obj):
        # TODO: set settings.DEFAULT_USER_AVATAR
        return obj.avatar.url if obj.avatar else None
    
    def get_number_of_posts(self, obj):
        return obj.posts.count()
    
    def get_followers_count(self, obj):
        return obj.followers.count()
    
    def get_following_count(self, obj):
        return obj.following.count()
    
    def get_posts_that_write_by_user_url(self, obj):
        return reverse('blog:post-list') +  "?" + urlencode({'search': obj.username})
    
    def get_likes_posts_url(self, obj):
        return reverse('blog:user-likes')
    
    def get_follower_list_url(self, obj):
        return reverse('auth:follow-followers-list')
    
    def get_following_list_url(self, obj):
        return reverse('auth:follow-following-list')
    
    def get_bookmarked_posts_list_url(self, obj):
        return reverse('blog:user-bookmarks')
        