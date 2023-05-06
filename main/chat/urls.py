from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('<str:ref_code>', views.ref_home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>', views.user_profile, name='user_profile'),
    path('email-confirmation/', views.email_confirmation, name='email_confirmation'),
    path('register/', views.register_user, name='register'),
    path('users_online/', views.users_online, name='users_online'),
    path('wallet_history/', views.wallet_history, name='wallet_history'),
    path('referrals/', views.referrals, name='referrals'),
    path('donate/', views.donate, name='donate'),
    path('games/', views.games, name='games'),
    path('proceed_donate/', views.proceed_donate, name='proceed_donate'),
    path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_failed/', views.payment_failed, name='payment_failed'),
    path('play_game/', views.play_game, name='play_game'),
    re_path('users_count/', views.users_count, name='users_count'),
    re_path('game_state/', views.game_state, name='game_state'),
    re_path('chat_game/', views.chat_game, name='chat_game'),



]
