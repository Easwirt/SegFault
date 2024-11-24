from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods


def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/ai/process-query/')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'authenticate/login.html')

def register_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['confirmPassword']  # Match the field names in the HTML

        if password == password2:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username is already taken')
                return redirect('register_user')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Email is already registered')
                return redirect('register_user')
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()
                messages.success(request, 'Registration successful. Please log in.')
                return redirect('login_user')
        else:
            messages.error(request, 'Passwords do not match')
            return redirect('register_user')
    else:
        return render(request, 'authenticate/register.html')

@login_required(login_url='/auth/login_user')
@ensure_csrf_cookie
@require_http_methods(["POST"])
def logout_user(request):
    if request.method == 'POST':
        try:
            logout(request)
            return JsonResponse({
                'status': 'success',
                'message': 'Successfully logged out'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
