from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('auth/', include('accounts.urls', namespace='auth')),
    path('', include('blog.urls', namespace='blog')),
    path('notification/', include('notifications.urls', namespace='notifications'))
]
