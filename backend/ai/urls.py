# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('process-query/', views.process_query_and_visualize, name='process_query'),
]