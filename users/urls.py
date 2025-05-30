from django.urls import path, reverse_lazy # Import reverse_lazy
from . import views
from django.contrib.auth import views as auth_views # Import Django's auth views

app_name = 'users'
urlpatterns = [
    path('',views.home_view,name='home'),
    path('login/', views.LoginView, name='login'),
    path('signup/', views.SignUpView, name='signup'),
    path('logout/', views.LogoutView, name='logout'),
    path('api/receive_packet/', views.receive_packet_view, name='receive_packet'),
# --- API Endpoint for RF Agent Data --- ADD THIS ---
    path('api/receive_rf_data/', views.receive_rf_data_view, name='receive_rf_data'),
    # --- End API Endpoint ---
    path('rf_scanner/', views.rf_scanner_view, name='rf_scanner'),  # ADD THIS

    # --- Password Reset URLs --- ADD THESE ---
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='users/password_reset_form.html', # Template for asking email
            email_template_name='users/password_reset_email.html', # Template for email content
            subject_template_name='users/password_reset_subject.html', # Template for email subject
            success_url=reverse_lazy('users:password_reset_done') # Use reverse_lazy for URL name
        ),
        name='password_reset'
    ),
    path(
        'password_reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='users/password_reset_done.html' # Template confirming email sent
        ),
        name='password_reset_done'
    ),
    path(
        'reset/<uidb64>/<token>/', # URL contains user ID (encoded) and token
        auth_views.PasswordResetConfirmView.as_view(
            template_name='users/password_reset_confirm.html', # Template to enter new password
            success_url=reverse_lazy('users:password_reset_complete') # Use reverse_lazy for URL name
        ),
        name='password_reset_confirm'
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='users/password_reset_complete.html' # Template confirming password changed
        ),
        name='password_reset_complete'
    ),
    # --- End Password Reset URLs ---

]