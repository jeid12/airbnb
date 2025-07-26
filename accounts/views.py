
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .forms import UserRegistrationForm
from .models import User
from django.contrib import messages

# accounts/views.py

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            User.objects.create(
                user=user,
                profile_picture=form.cleaned_data.get('profile_picture'),
                phone_number=form.cleaned_data.get('phone_number'),
                bio=form.cleaned_data.get('bio'),
                role=form.cleaned_data.get('role'),
            )
            messages.success(request, "Account created successfully. Please log in.")
            return redirect('accounts:login')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})
