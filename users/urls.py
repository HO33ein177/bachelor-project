from django.urls import path

from . import views

app_name = 'users'
urlpatterns = [
    path('',views.home_view,name='home'),
    path('login/', views.LoginView, name='login'),
    path('signup/', views.SignUpView, name='signup'),
    path('logout/', views.LogoutView, name='logout'),
    path

]