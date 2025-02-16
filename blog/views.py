from django.shortcuts import render
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework.views import Response, status, APIView
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.throttling import UserRateThrottle
from . import serializers
from .models import Tag, Post, PostImage, Like, Comment, BookMark
from .pagination import PostListPagination, CommentListPagination
from accounts.models import Role, Permission
from .permissions import CanUserWritePost, OwnerAndAdminOnly, CanUserWriteComment, CanUserBookMarkPosts
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

class TagListApiView(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    serializer_class = serializers.TagListSerializer

class PostsByTagApiView(mixins.ListModelMixin, viewsets.GenericViewSet):
    pagination_class = PostListPagination
    serializer_class = serializers.PostsListSerializer

    def get_queryset(self):
        user = self.request.user

        if user.is_authenticated and user.can(Permission.ADMIN):
            return Post.objects.all()
        
        return Post.active_objects.get_premium_posts(premium=user.is_authenticated and user.is_premium)
    
    def list(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        
        if not slug:
            return Response({'error': 'Tag slug should provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset().filter(tag__slug=slug)

        page = self.paginate_queryset(queryset)

        if page:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            return Response(result.data, status=status.HTTP_200_OK)

        serailizer = self.get_serializer(queryset, many=True)
        return Response(serailizer.data, status=status.HTTP_200_OK)


class LikeApiView(viewsets.GenericViewSet):
    
    def _get_post(self, post_slug=None):
        if not post_slug:
            return Response({'error': 'Post slug is required'}, status=status.HTTP_400_BAD_REQUEST)
        return get_object_or_404(Post, slug=post_slug)
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return []
    
    def retrieve(self, request, post_slug=None):
        post = self._get_post(post_slug)
        
        post_likes_count = post.post_like_count

        # Check if the user has liked the post
        user = request.user if request.user.is_authenticated else None
        does_user_likes = post.likes.filter(user=user).exists()
        
        return Response(
            {'post_likes_count': post_likes_count, 'does_user_likes':does_user_likes},
            status=status.HTTP_200_OK
        )

    def create(self, request, post_slug=None):
        post = self._get_post(post_slug)

        like_obj, created = Like.objects.get_or_create(post=post, user=request.user)
        
        if created:
            return Response({'success': 'You Liked thise post'}, status=status.HTTP_201_CREATED)
        
        like_obj.delete()
        return Response({'success': 'You unliked this post'}, status=status.HTTP_204_NO_CONTENT)
    
class ListAndCreateCommentApiView(viewsets.ViewSet, viewsets.GenericViewSet):
    pagination_class = CommentListPagination
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'

    def _get_post(self, post_slug=None):
        if not post_slug:
            return Response({'error': 'Post slug is required'}, status=status.HTTP_400_BAD_REQUEST)
        return get_object_or_404(Post, slug=post_slug)  

    def get_permissions(self):
        permission_classes = []
        if self.action in ['create', 'reply']:
            permission_classes = [IsAuthenticated, CanUserWriteComment]
        return [perm() for perm in permission_classes]
    
    def get_serializer_class(self, *args, **kwargs):
        if self.action == 'list':
            return serializers.CommentSerializer
        return serializers.CreateCommentSerializer
    
    def get_queryset(self, post_slug=None):
        post = self._get_post(post_slug)
        return Comment.objects.filter(is_active=True, post=post, level=0)
    
    def get_object(self, uuid=None, post_slug=None):
        obj = get_object_or_404(self.get_queryset(post_slug), uuid=self.kwargs.get(self.lookup_url_kwarg))
        self.check_object_permissions(self.request, obj)
        return obj
    
    def list(self, request, post_slug=None):
        user = request.user
        qs = self.get_queryset(post_slug)
        comment_paginate_qs = self.paginate_queryset(qs)

        post = self._get_post(post_slug)
        is_owner = post.author == request.user or (user.is_authenticated and user.can(Permission.ADMIN))

        context = {
            'request': request,
            'is_owner': is_owner
        }

        if comment_paginate_qs is not None:
            serializer = self.get_serializer(comment_paginate_qs, many=True, context=context)
            return Response(self.get_paginated_response(serializer.data).data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(qs, many=True, context=context)
        return Response(serializer.data)
        # TODO: context: is_owner
    
    def create(self, request, post_slug=None):
        post = self._get_post(post_slug)

        context = {
            'request': request,
            'post': post,
        }

        serailizer = self.get_serializer(data=request.data, context=context)
        serailizer.is_valid(raise_exception=True)
        serailizer.save()

        return Response({'success': 'Comment Created'}, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_name='reply')
    def reply(self, request, post_slug=None, uuid=None, *args, **kwargs):
        post = self._get_post(post_slug)
        parent_comment = self.get_object(uuid, post_slug)
        context = {
            'request': request,
            'post': post,
            'parent_comment': parent_comment
        }
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': 'Comment Created'}, status=status.HTTP_201_CREATED)

class UpdateAndDeleteCommentApiView(viewsets.ModelViewSet):
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    permission_classes = [IsAuthenticated, CanUserWriteComment]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.CommentSerializer
        else:
            if self.request.user.can(Permission.ADMIN):
                return serializers.AdminUpdateCommentSerializer
            return serializers.UsersUpdateCommentSerializer

    def get_queryset(self):
        if self.request.user.can(Permission.ADMIN):
            return Comment.objects.all()
        return Comment.objects.filter(is_active=True, user=self.request.user)

    def get_object(self):
        uuid = self.kwargs.get(self.lookup_url_kwarg)
        obj = get_object_or_404(self.get_queryset(), uuid=uuid)
        self.check_object_permissions(self.request, obj)
        return obj

    def destroy(self, request, *args, **kwargs):
        comment_obj = self.get_object()
        comment_obj.is_active = False
        comment_obj.save()
        return Response({'success': 'Comment deleted'}, status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class BookMarkApiView(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, CanUserBookMarkPosts]
    
    def get_queryset(self):
        return Post.active_objects.filter(premium=self.request.user.is_premium)
    
    def get_object(self):
        return get_object_or_404(self.get_queryset(), slug=self.kwargs.get('post_slug'))
    
    @action(detail=True, methods=['POST'], url_path='bookmark/')
    def bookmark(self, request, *args, **kwargs):
        post_obj = self.get_object()

        bookmark_obj, created = BookMark.objects.get_or_create(user=request.user, post=post_obj)

        if created:
            return Response({'success': 'Post bookmarked'}, status=status.HTTP_201_CREATED)
        
        bookmark_obj.delete()
        return Response({'success': 'Post Unbookmarked'}, status=status.HTTP_204_NO_CONTENT)


