from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django import forms
from django.contrib.auth import get_user_model


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=254, widget=forms.EmailInput(attrs={'placeholder': 'Электронная почта', 'class':'input_modal', 'id':'login_email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Пароль', 'class':'input_modal'}))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user_model = get_user_model()
            try:
                user = user_model.objects.get(email=email)
            except user_model.DoesNotExist:
                self.add_error('email', 'User with this email does not exist.')
                return

            if not user.check_password(password):
                self.add_error('password', 'Password is incorrect.')

class MyUserCreationForm(UserCreationForm):

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Пароль', 'class':'input_modal'})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Подтвердите пароль', 'class':'input_modal'}),
        strip=False,
        help_text="Enter the same password as before, for verification."
    )

    class Meta:
        model = get_user_model()
        fields = ['username', 'email']

        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Электронная почта', 'class':'input_modal'}),
            'password1': forms.PasswordInput(attrs={'placeholder': 'Пароль', 'class':'input_modal'}),
            'password2': forms.PasswordInput(attrs={'placeholder': 'Подтвердите пароль'}),
            'username': forms.TextInput(attrs={'placeholder': 'Логин', 'class':'input_modal'}),
        }

    
        

class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=4,
        decimal_places=2,
        min_value=0.01,
        help_text='Amount to withdraw',
        label='Amount'
    )
    payeer_account = forms.CharField(
        help_text='Your Payeer account',
        label='Payeer Account'
    )
    
class DepositForm(forms.Form):
    amount = forms.DecimalField(max_digits=5, decimal_places=2, min_value=3, help_text='Введите сумму')