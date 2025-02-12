from django.urls import path

from . import views

app_name = 'auth'

urlpatterns = [
    path('login/', views.LoginApiView.as_view(), name='login'),
    path('logout/', views.LogoutApiView.as_view(), name='logout'),
    path('register/', views.RegistrationApiView.as_view(), name='register'),
    path('account-verify/', views.AccountVerificationApiView.as_view(), name='account-verify'),
    path('user/change-password/', views.ChangePasswordApiView.as_view(), name='change-password'),
]
