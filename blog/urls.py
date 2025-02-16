from django.urls import path, include
from rest_framework.routers import SimpleRouter, DefaultRouter
from rest_framework_nested import routers

from . import views

app_name = 'blog'

router = DefaultRouter()
router.register(r'post', views.PostApiView, basename='post')
router.register(r'posts/bookmarks', views.BookMarkApiView, basename='post-bookmark')

image_router = routers.NestedSimpleRouter(router, r'post', lookup='post')
image_router.register(r'images', views.ImagesApiView, basename='post-images')

comment_nested_router = routers.NestedSimpleRouter(router, f'post', lookup='post')
comment_nested_router.register(f'comments', views.ListAndCreateCommentApiView, basename='post-commnts')


urlpatterns = [
    path('', include(router.urls)),
    path('', include(image_router.urls)),
    path('', include(comment_nested_router.urls)),
    path('post/<slug:post_slug>/bookmark/', views.BookMarkApiView.as_view({'post': 'bookmark'}), name='post-bookmark'),
    path('post/<slug:post_slug>/likes', views.LikeApiView.as_view({'get': 'retrieve'}), name='likes'),
    path('post/<slug:post_slug>/like/', views.LikeApiView.as_view({'post': 'create'}), name='toggle-like'),
    path('comment/<uuid:uuid>/',
         views.UpdateAndDeleteCommentApiView.as_view(
             {'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='comment'),
    path('tags/', views.TagListApiView.as_view({'get': 'list'}), name='tag-list'),
    path('post/tags/<slug:slug>/', views.PostsByTagApiView.as_view({'get': 'list'}), name='post-by-tag'),

]