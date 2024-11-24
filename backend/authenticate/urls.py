from django.urls import path, include
from . import views

urlpatterns = [
    path('login_user/', views.login_user, name='login_user'),
    path('register_user/', views.register_user, name='register_user'),
]