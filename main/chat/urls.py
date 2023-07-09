from django.urls import path, re_path
from . import views

urlpatterns = [
path('', views.home, name='home'),
    path('<str:ref_code>', views.ref_home, name='home'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/<str:username>', views.user_profile, name='user_profile'),
    path('users_online/', views.users_online, name='users_online'),
    path('wallet_history/', views.wallet_history, name='wallet_history'),
    path('referrals/', views.referrals, name='referrals'),

    path('balance/', views.balance, name='balance'),
    path('donate/', views.donate, name='donate'),
    path('withdraw/', views.withdraw, name='withdraw'),
    path('proceed_withdraw/', views.proceed_withdraw, name='proceed_withdraw'),

    path('games/', views.games, name='games'),
    path('proceed_donate/', views.proceed_donate, name='proceed_donate'),
    path('payment_success/', views.payment_success, name='payment_success'),
    path('payment_failed/', views.payment_failed, name='payment_failed'),
    path('play_game/', views.play_game, name='play_game'),
    path('bet_game/', views.bet_game, name='bet_game'),
    re_path('users_count/', views.users_count, name='users_count'),
    path('chat_game/<int:pk>', views.chat_game, name='chat_game'),
    path('chat_game/delete/<int:game_id>', views.delete_game, name='delete_game'),
    path('bet_history/', views.bet_history, name='bet_history'),

    #For admin only
    path('withdrawal_requests/', views.withdrawal_requests, name='withdrawal_requests'),
    path('all_users/', views.all_users, name='all_users'),
    path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),

]
