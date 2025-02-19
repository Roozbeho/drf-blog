from django.shortcuts import render
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework.views import Response, status, APIView
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.throttling import UserRateThrottle
from rest_framework.filters import SearchFilter
from django.urls import resolve
from django.contrib.contenttypes.models import ContentType

from . import serializers
from .models import Tag, Post, PostImage, Like, Comment, BookMark
from .pagination import PostListPagination, CommentListPagination
from accounts.models import Role, Permission
from .permissions import CanUserWritePost, OwnerAndAdminOnly, CanUserWriteComment, CanUserBookMarkPosts
from .ordering import CustomOrderingFilter
import asyncio
from notifications import utils
from notifications.models import Notification
from activity_log.mixins import ActivityLogMixin
from activity_log.models import ActivityLog


class CreatePostRequestThrottle(UserRateThrottle):
    rate = '300/hour'
class PostApiView(ActivityLogMixin, viewsets.ModelViewSet):
    pagination_class = PostListPagination
    filter_backends = (CustomOrderingFilter, )
    search_fields = ['=author__username']
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

class TagListApiView(ActivityLogMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Tag.objects.all()
    serializer_class = serializers.TagListSerializer

class PostsByTagApiView(ActivityLogMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
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


class LikeApiView(ActivityLogMixin, viewsets.GenericViewSet):
    serializer_class = serializers.PostsListSerializer
    IS_LIKE = False

    def get_queryset(self):
        return Post.active_objects.filter(
            premium=self.request.user.is_authenticated and self.request.user.is_premium
        )
    
    def get_object(self):
        return get_object_or_404(self.get_queryset(), slug=self.kwargs['post_slug'])
    
    def get_permissions(self):
        if self.action in ['create', 'list']:
            return [IsAuthenticated()]
        return []
    
    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset().filter(likes__user=user)
        page = self.paginate_queryset(queryset)

        if page:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            return Response(result.data, status=status.HTTP_200_OK)

        serailizer = self.get_serializer(queryset, many=True)
        return Response(serailizer.data, status=status.HTTP_200_OK)
    
    def retrieve(self, request, post_slug=None):
        post = self.get_object()
        
        post_likes_count = post.post_like_count

        # Check if the user has liked the post
        user = request.user if request.user.is_authenticated else None
        does_user_likes = post.likes.filter(user=user).exists()
        
        return Response(
            {'post_likes_count': post_likes_count, 'does_user_likes':does_user_likes},
            status=status.HTTP_200_OK
        )

    def create(self, request, post_slug=None):
        post = self.get_object()

        like_obj = Like.objects.filter(post=post, user=request.user).first()
        if not like_obj:
            like_obj = Like.objects.create(post=post, user=request.user)
            self.IS_LIKE = True
            
            post_author = post.author
            message = 'someone liked your post'

            Notification.objects.create(user=post_author, message=message)
            utils.send_notification(post_author.id, message)

            return Response({'success': 'You liked this post'}, status=status.HTTP_201_CREATED)

        like_obj.delete()
        self.IS_LIKE = False
        return Response({'success': 'You unliked this post'}, status=status.HTTP_200_OK)
    
    def _get_action_type(self, request):
        if self.action == 'create':
            if self.IS_LIKE:
                return ActivityLog.Activity_Type.LIKE
            return ActivityLog.Activity_Type.UNLIKE
        return super()._get_action_type(request)

class ListAndCreateCommentApiView(ActivityLogMixin, viewsets.ViewSet, viewsets.GenericViewSet):
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
        self.query_set = Comment.objects.filter(is_active=True, post=post, level=0)
        return self.query_set
    
    def get_object(self, uuid=None, post_slug=None):
        self.comment_obj = get_object_or_404(self.get_queryset(post_slug), uuid=self.kwargs.get(self.lookup_url_kwarg))
        self.check_object_permissions(self.request, self.comment_obj)
        return self.comment_obj
    
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
        
    def _build_log_messsage(self, request):
        return f'\
            User: {self._get_user_mixin(request)} \
            -- Action Type: { \
                    self._get_action_type(request) \
                    if self.action == 'list' else \
                    ActivityLog.Activity_Type.COMMENT \
                    } \
            -- Path: {request.path} \
            -- Path Name: {resolve(request.path_info).url_name}'
    def _write_log(self, request, response):
        activitylog_instance = super()._write_log(request, response)
        if activitylog_instance:
            with transaction.atomic():
                activitylog_instance.content_type = ContentType.objects.get_for_model(Comment)
                activitylog_instance.object_id = getattr(self, 'comment_obj', None)
                activitylog_instance.save()

class UpdateAndDeleteCommentApiView(ActivityLogMixin, viewsets.ModelViewSet):
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
        self.comment_obj = comment_obj.pk
        comment_obj.is_active = False
        comment_obj.save()
        return Response({'success': 'Comment deleted'}, status=status.HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

    def _write_log(self, request, response):
        activitylog_instance = super()._write_log(request, response)
        if activitylog_instance and self.action == 'destroy':
            activitylog_instance.object_id = getattr(self, 'comment_obj', None)
            activitylog_instance.save()

class BookMarkApiView(ActivityLogMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated, CanUserBookMarkPosts]
    pagination_class = PostListPagination
    serializer_class = serializers.PostsListSerializer 

    def get_queryset(self):
        return Post.objects.filter(bookmarks__user=self.request.user)

    def get_object(self):
        return get_object_or_404(
            Post.active_objects.filter(premium=self.request.user.is_premium),
            slug=self.kwargs.get('post_slug')
        )

    @action(detail=True, methods=['POST'], url_path='bookmark')
    def bookmark(self, request, post_slug=None):
        post_obj = self.get_object()
        self.BOOKMARK = False

        bookmark_obj, created = BookMark.objects.get_or_create(user=request.user, post=post_obj)

        if created:
            self.BOOKMARK = True
            return Response({'success': 'Post bookmarked'}, status=status.HTTP_201_CREATED)
        
        bookmark_obj.delete()
        return Response({'success': 'Post unbookmarked'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['GET'], url_path='bookmarks')
    def list_bookmarks(self, request):

        bookmarks_queryset = Post.objects.filter(bookmarks__user=request.user)
        page = self.paginate_queryset(bookmarks_queryset)

        if page:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            return Response(result.data, status=status.HTTP_200_OK)

        serailizer = self.get_serializer(bookmarks_queryset, many=True)
        return Response(serailizer.data, status=status.HTTP_200_OK)
    
    def _get_action_type(self, request):
        if self.action == 'bookmark':
            if self.BOOKMARK:
                return ActivityLog.Activity_Type.BOOKMARK
            return ActivityLog.Activity_Type.UNBOOKMARK
        return super()._get_action_type(request)

    def _write_log(self, request, response):
        activitylog_instance = super()._write_log(request, response)
        if activitylog_instance and self.action == 'list_bookmarks':
            activitylog_instance.content_type = ContentType.objects.get_for_model(BookMark)
            activitylog_instance.save()