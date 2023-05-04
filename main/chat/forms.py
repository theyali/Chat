from django.forms import ModelForm
from django.contrib.auth.forms import UserCreationForm
from .models import User
from django import forms
from django.contrib.auth import get_user_model

class MyUserCreationForm(UserCreationForm):

    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter your password'})
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm your password'}),
        strip=False,
        help_text="Enter the same password as before, for verification."
    )

    class Meta:
        model = get_user_model()
        fields = ['username', 'email']

        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'password1': forms.PasswordInput(attrs={'placeholder': 'Password'}),
            'password2': forms.PasswordInput(attrs={'placeholder': 'Confirm your Password'}),
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),
        }

    
        

class WithdrawalForm(forms.Form):
    amount = forms.DecimalField(max_digits=4, decimal_places=2, min_value=0.01, help_text='Amount to withdraw')
    paypal_email = forms.EmailField(help_text='Your PayPal email address')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if self.user.balance < amount:
            raise forms.ValidationError('Insufficient balance.')
        return amount
    
class DepositForm(forms.Form):
    amount = forms.DecimalField(max_digits=5, decimal_places=2, min_value=3, help_text='Введите сумму')