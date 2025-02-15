from django.urls import path, include
from rest_framework.routers import SimpleRouter, DefaultRouter
from rest_framework_nested import routers

from . import views

app_name = 'blog'

router = DefaultRouter()
router.register(r'post', views.PostApiView, basename='post')

image_router = routers.NestedSimpleRouter(router, r'post', lookup='post')
image_router.register(r'images', views.ImagesApiView, basename='post-images')

comment_nested_router = routers.NestedSimpleRouter(router, f'post', lookup='post')
comment_nested_router.register(f'comments', views.ListAndCreateCommentApiView, basename='post-commnts')

# comment_router = DefaultRouter()
# comment_router.register(r'comment', views.UpdateAndDeleteCommentApiView, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(image_router.urls)),
    path('', include(comment_nested_router.urls)),
    # path('', include(comment_router.urls)),
    path('post/<slug:post_slug>/likes', views.LikeApiView.as_view({'get': 'retrieve'}), name='likes'),
    path('post/<slug:post_slug>/like/', views.LikeApiView.as_view({'post': 'create'}), name='toggle-like'),
    path('comment/<uuid:uuid>/',
         views.UpdateAndDeleteCommentApiView.as_view(
             {'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='comment')
    # path('post/<slug:post_slug>/comments/',
    #      views.ListAndCreateCommentApiView.as_view({'get': 'list', 'post': 'create'}), name='comment'),
    # path('post/<slug:post_slug>/comments/<uuid:uuid>/reply',
    #      views.ListAndCreateCommentApiView.as_view({'post': 'reply'}), name='reply')

]