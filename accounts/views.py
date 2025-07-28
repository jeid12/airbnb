from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from .forms import UserRegistrationForm

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            
            user=form.save()

            # Log the user in after successful registration
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Registration successful. You are now logged in.")
                return redirect('listings:home')
            else:
                messages.error(request, "Registration successful, but login failed. Please try logging in manually.")



           
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})
