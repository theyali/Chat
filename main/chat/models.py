from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.crypto import get_random_string
from .utils import generate_ref_code
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
    is_online = models.BooleanField(default=False)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    bio = models.TextField(max_length=150, blank=True, null=True)
    referal_code = models.CharField(max_length=12, blank=True)
    recomended_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='ref_by')
    is_searching_game = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s profile"
    
class Wallet(models.Model):
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    wallet_number = models.CharField(max_length=50, unique=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.user_profile.user.username + ' - Wallet'
    
class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=True)
    amount = models.DecimalField(max_digits=5, decimal_places=2)
    status = models.CharField(max_length=10, choices=[('pending', 'Ожидает'), ('completed', 'Выполнено'), ('failed', 'Не выполнено')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Transaction #{self.id} ({self.user.username}): {self.amount}'

    
class Game(models.Model):
    player1 = models.ForeignKey(User, related_name='games_as_player1', on_delete=models.CASCADE, blank=True)
    player2 = models.ForeignKey(User, related_name='games_as_player2', on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField(auto_now_add=True)
    is_searching = models.BooleanField(default=True)
    bet = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_controlled_by_site = models.BooleanField(default=False) # Добавлено
    winner = models.ForeignKey(User, related_name='games_won', on_delete=models.SET_NULL, null=True, blank=True) # Добавлено
    random_number = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Game ({self.player1} vs {self.player2})"

    

class Game_Bet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    current_game = models.ForeignKey(Game, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_winning = models.BooleanField(default=False)
    is_returned = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s bet of {self.amount} on {self.current_game}"

