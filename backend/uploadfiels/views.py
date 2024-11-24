# views.py
import os
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.shortcuts import resolve_url
from django.utils.http import urlencode
from functools import wraps
from .models import UserUpload


def custom_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            path = request.build_absolute_uri()
            login_url = resolve_url('/auth/user_login/')
            redirect_url = f"{login_url}?{REDIRECT_FIELD_NAME}={path}"
            return HttpResponseForbidden(
                f'<script>window.location.href = "{redirect_url}";</script>'
            )
        return view_func(request, *args, **kwargs)

    return wrapper


@custom_login_required
def upload_file(request):
    if request.method == 'POST' and 'file' in request.FILES:
        uploaded_file = request.FILES['file']

        # Validate file type
        content_type = uploaded_file.content_type
        if content_type not in ['text/csv', 'application/vnd.ms-excel']:
            return HttpResponse('Invalid file type. Please upload a CSV file.', status=400)

        # Validate file extension
        file_extension = os.path.splitext(uploaded_file.name)[1].lower()
        if file_extension != '.csv':
            return HttpResponse('Invalid file extension. Please upload a CSV file.', status=400)

        # Validate file size (e.g., max 5MB)
        if uploaded_file.size > 5 * 1024 * 1024:
            return HttpResponse('File too large. Maximum size is 5MB.', status=400)

        try:
            # Generate a safe filename with user prefix
            base_filename = default_storage.get_valid_name(uploaded_file.name)
            filename = f"{request.user.username}_{base_filename}"

            # Create the full path
            save_path = os.path.join(settings.MEDIA_ROOT, 'csv', filename)

            # Ensure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)

            # Save the file
            with default_storage.open(save_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Create UserUpload record
            user_upload = UserUpload.objects.create(
                user=request.user,
                file=f'csv/{filename}',
                original_filename=uploaded_file.name,
                file_size=uploaded_file.size
            )

            return HttpResponse(f'File "{filename}" uploaded successfully!')

        except Exception as e:
            return HttpResponse(f'Error saving file: {str(e)}', status=500)

    # Get user's previous uploads
    user_uploads = UserUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'upload.html', {'user_uploads': user_uploads})


@custom_login_required
def list_uploads(request):
    user_uploads = UserUpload.objects.filter(user=request.user).order_by('-uploaded_at')
    return render(request, 'list_uploads.html', {'uploads': user_uploads})


@custom_login_required
def delete_upload(request, upload_id):
    try:
        print(id, request.user.username)
        upload = UserUpload.objects.get(id=upload_id, user=request.user)
        print(upload.file.name)
        if os.path.exists(upload.file.path):
            os.remove(upload.file.path)

        # Delete the database record
        upload.delete()
        return HttpResponse('File deleted successfully')
    except UserUpload.DoesNotExist:
        return HttpResponse('File not found', status=404)
    except Exception as e:
        return HttpResponse(f'Error deleting file: {str(e)}', status=500)