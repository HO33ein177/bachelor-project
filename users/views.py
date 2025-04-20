from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages

# Create your views here.
#
@login_required
def home_view(request):
    context = {}
    return render(request, 'home.html',context)


def SignUpView(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Account was created, welcome {user.username}')
            return redirect('users:home')
        else:
            messages.error(request, f'There was an error, please fix the errors')
    else:
        form = UserCreationForm()
        return render(request, 'signUp.html', {'form': form, 'title': 'Sign Up'})


def LoginView(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Account was created, welcome {username}')
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                else:
                    return redirect('users:home')
            else:
                messages.error(request, f'Username or password is incorrect')
        else:
            messages.error(request, f'There was an error, please fix the errors')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form, 'title': 'login'})


def LogoutView(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, f'You have been logged out successfully')
    return redirect('users/login')




