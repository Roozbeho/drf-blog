from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'auth'

router = DefaultRouter()
router.register(r'follow', views.FollowApiView, basename='follow')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', views.LoginApiView.as_view(), name='login'),
    path('logout/', views.LogoutApiView.as_view(), name='logout'),
    path('register/', views.RegistrationApiView.as_view(), name='register'),
    path('account-verify/', views.AccountVerificationApiView.as_view(), name='account-verify'),
    path('user/change-password/', views.ChangePasswordApiView.as_view(), name='change-password'),
    path('user/<str:username>/', views.UserProfileApiView.as_view({'get': 'retrieve'}), name='user-profil'),
]
