# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User # Import the User model

class UserRegisterForm(UserCreationForm):
    # Add an email field
    email = forms.EmailField(required=True, help_text='Required. Used for password recovery.')

    class Meta(UserCreationForm.Meta):
        # Inherit from the default User model
        model = User
        # Specify fields to include: default UserCreationForm fields + email
        fields = UserCreationForm.Meta.fields + ('email',)

    def clean_email(self):
        """
        Optional: Add validation to ensure the email is unique if desired.
        """
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email