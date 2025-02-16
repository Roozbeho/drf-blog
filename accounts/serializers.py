import re

from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.validators import UniqueValidator

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