from django.urls import path, include
from rest_framework.routers import SimpleRouter, DefaultRouter
from rest_framework_nested import routers

from . import views

app_name = 'blog'

router = DefaultRouter()
router.register(r'post', views.PostApiView, basename='post')

image_router = routers.NestedSimpleRouter(router, r'post', lookup='post')
image_router.register(r'images', views.ImagesApiView, basename='post-images')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(image_router.urls))
]
