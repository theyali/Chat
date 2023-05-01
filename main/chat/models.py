from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
from .utils import generate_ref_code
import uuid
# Create your models here.

class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=254)
    email_verification_code = models.CharField(max_length=10, blank=True)

    USERNAME_FIELD= 'email'
    REQUIRED_FIELDS = []

    def generate_email_verification_code(self):
        """
        Generates a random 6-digit alphanumeric code for email verification.
        """
        code = get_random_string(length=6, allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        self.email_verification_code = code
        self.save()
        return code
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    bio = models.TextField(max_length=150, blank=True, null=True)
    referal_code = models.CharField(max_length=12, blank=True)
    recomended_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='ref_by')
    # add more fields as needed

    def __str__(self):
        return f"{self.user.username}'s profile"

    def save(self, *args, **kwargs):
        if self.referal_code == "":
            code = generate_ref_code()
            self.referal_code = code
        super().save(*args, **kwargs)
        Wallet.objects.create(user_profile=self, wallet_number=str(uuid.uuid4()))
    
class Wallet(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    wallet_number = models.CharField(max_length=50, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.user_profile.user.username + ' - Wallet'
    
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=10, choices=[('pending', 'Ожидает'), ('completed', 'Выполнено'), ('failed', 'Не выполнено')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Transaction #{self.id} ({self.user.username}): {self.amount}'