from django.urls import path
from . import views
from .views import CreatePaymentView, ExecutePaymentView

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

    path('paypal/create/', CreatePaymentView.as_view(), name='paypal_create'),
    path('paypal/execute/', ExecutePaymentView.as_view(), name='paypal_execute'),

]
