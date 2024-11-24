from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_file, name='upload_file'),
    path('uploads/', views.list_uploads, name='list_uploads'),
    path('delete-upload/<int:upload_id>/', views.delete_upload, name='delete_upload')
]