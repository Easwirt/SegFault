# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('generate-sql/', views.generate_sql_query, name='generate_sql_query'),
]
