from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages

def login_user(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
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
