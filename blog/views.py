from django.shortcuts import render
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import Response, status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.throttling import UserRateThrottle
from . import serializers
from .models import Tag, Post, PostImage
from .pagination import PostListPagination
from accounts.models import Role, Permission
from .permissions import CanUserWritePost, OwnerAndAdminOnly
from .ordering import CustomOrderingFilter


class CreatePostRequestThrottle(UserRateThrottle):
    rate = '300/hour'
class PostApiView(viewsets.ModelViewSet):
    pagination_class = PostListPagination
    filter_backends = (CustomOrderingFilter, )
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.PostsListSerializer
        elif self.action in 'retrieve':
            return serializers.PostDetailSerializer
        return serializers.CreateAndManagementPostSerializer
        
    def get_throttles(self):
        if self.action == 'create':
            return [CreatePostRequestThrottle()]
        return []
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_permissions(self):
        permission_classes = []
        if self.action == 'create':
            permission_classes = [IsAuthenticated, CanUserWritePost]
        elif self.action in ['destroy', 'update']:
            permission_classes = [IsAuthenticated, OwnerAndAdminOnly]
        return [perm() for perm in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            return Post.active_objects.get_premium_posts(user.is_premium)
        return Post.active_objects.all()

    def get_object(self):
        obj = super().get_object()
        obj.visit_counter += 1
        obj.save()
        obj.refresh_from_db()
        return obj

    def list(self, request):
        qs = self.filter_queryset(self.get_queryset())
        post_paginate_qs = self.paginate_queryset(qs)
        serializer = self.get_serializer(post_paginate_qs, many=True)

        result = self.get_paginated_response(serializer.data)

        return Response(result.data, status=status.HTTP_200_OK)
    
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save()

        return Response({'success': 'Your post has been deleted'}, status=status.HTTP_200_OK)
    
class ImagesApiView(viewsets.ModelViewSet):
    serializer_class = serializers.PostImageSerializer
    permission_classes = [IsAuthenticated, OwnerAndAdminOnly]
    lookup_field = 'pk'
    lookup_url_kwarg = 'pk'

    def _get_post(self, post_slug):
        """Fetch post using slug and check obj permissions"""
        post = get_object_or_404(Post, slug=post_slug)
        self.check_object_permissions(self.request, post)
        return post

    def get_queryset(self, post_slug=None):
        post = self._get_post(post_slug)
        return PostImage.objects.filter(post=post)
    
    def get_object(self, pk=None, post_slug=None):
        return get_object_or_404(self.get_queryset(post_slug), pk=pk)
    
    def list(self, request, post_slug=None):
        if not post_slug:
            return Response({'error': 'post_slug not found'}, status=status.HTTP_400_BAD_REQUEST)

        queryset = self.get_queryset(post_slug)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None, post_slug=None):
        if not post_slug:
            return Response({'error': 'post_slug not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        obj = self.get_object(pk, post_slug)
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @transaction.atomic
    def create(self, request, post_slug=None):
        if not post_slug:
            return Response({'error': 'Post slug is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = request.FILES
        data['post'] = self._get_post(post_slug).slug

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def destroy(self, request, pk=None, post_slug=None):
        post = self._get_post(post_slug)

        image = get_object_or_404(PostImage, pk=pk, post=post)
        image.delete()
        return Response({'success': 'image deleted'}, status=status.HTTP_204_NO_CONTENT)
    



    
    
