import json
import random
import uuid
from django.shortcuts import render, redirect,  get_object_or_404 
from django.contrib import messages
from .utils import DecimalEncoder, generate_ref_code
from .models import User, UserProfile, Wallet, Transaction, Game, Game_Bet
from django.contrib.auth import authenticate, login, logout
from .forms import MyUserCreationForm, DepositForm, WithdrawalForm
from django.core.mail import send_mail
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.http import JsonResponse
from decimal import Decimal
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.views.decorators.http import require_http_methods
from django.db.models import Sum

# paypalrestsdk.configure({
#   "mode": "sandbox", # Режим Sandbox для тестирования
#   "client_id": "ARJCFqoUI6WIXxj7KC-9KHNBKqZiPRRHNFFr2WpJNGPuKQaXLRNDZsB-5vgbLBQovPzcnGJ8XFcGxnSQ", # Ваш Client ID
#   "client_secret": "EAmhZdjbHOYCk0v2j-Wm17hoqbvaNMHGsMtHfNv4jUcWFWHSXdTh7lszc-usvoSihU8K2GntlzzBtBXm" # Ваш Secret
# })


        
def get_online_users():
    """
    Returns a list of online user objects.
    """
    # Query all non-expired sessions
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    # Extract a list of user IDs from the session data
    user_ids = [s.get_decoded().get('_auth_user_id') for s in sessions if s.get_decoded().get('_auth_user_id') is not None]
    # Query all user objects with those IDs
    users = User.objects.filter(id__in=user_ids)
    # Return a list of distinct users
    return list(users.distinct())


def get_common_context(request):
    username=''
    try:
        wallet = request.wallet
        balance = wallet.balance
        username = request.user.username
    except:
        balance = ''
        username=''
    return {
        'balance': balance,
        'username':username
    }

def home(request):
    context= get_common_context(request)
    form = MyUserCreationForm()
    if request.method == "POST":
        form = MyUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            request.session["username"] = user.username
            user.is_active = False  # Set the user to inactive until email is confirmed
            user.save()
            confirmation_code = user.generate_email_verification_code()
            user.save()
            # Create UserProfile object for the new user
            try:
                user_profile = UserProfile(user=user ,recomended_by_id=request.session['ref_profile'])
                user_profile.save()
            except:
                user_profile = UserProfile(user=user)
                user_profile.save()
            user_profile = UserProfile.objects.select_for_update().get(user=user)
            user_profile.referal_code = generate_ref_code()
            user_profile.save() 
            Wallet.objects.create(user_profile=user_profile, wallet_number=str(uuid.uuid4()))
            # Send the confirmation email
            subject = 'Confirm your email address'
            message = f'Your confirmation code is {confirmation_code}'
            from_email = 'haciyev.ali@hotmail.com'
            to_email = [user.email]
            send_mail(subject, message,from_email, to_email)
            return JsonResponse({'status': 'success', 'message': 'Registration successful! Please confirm your email.'})
        else:
            messages.error(request, "Произошла ошибка во время регистрации")
            return JsonResponse({'status': 'error', 'message': 'Произошла ошибка во время регистрации', 'redirect': 'home'}, status=400)
    context['form']=form
    return render(request, 'chat/home.html',context=context)

def ref_home(request, *args, **kwargs):
    code = str(kwargs.get('ref_code'))
    try:
        profile = UserProfile.objects.get(referal_code=code)
        request.session['ref_profile'] = profile.user_id
    except:
        return redirect('home')
    context = get_common_context(request)
    return render(request, 'chat/home.html',context=context)

@login_required
def profile(request):
    context = get_common_context(request)
    return render(request, 'chat/profile.html', context=context)

def login_user(request):
    if request.method == "POST":
        email = request.POST.get('email').lower()
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            user_profile = get_object_or_404(UserProfile, user=user)
            user_profile.is_online = True
            user_profile.save()
            wallet = get_object_or_404(Wallet, user_profile=user_profile)
            request.session['wallet_id'] = wallet.id
            return redirect("profile")
        else:
            messages.error(request, "Почта или пароль неверны")
    return render(request, 'chat/home.html', {})

@login_required
def logout_user(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    user_profile.is_online = False
    user_profile.save()
    logout(request)
    return redirect('home')


def email_confirmation(request):
    # check if user is authenticated (i.e., has just registered)
    if request.session.get("username") is None:
        return redirect("home")

    if request.method == "POST":
        code = request.POST.get("code")
        user = User.objects.get(username=request.session.get("username"))
        if code == user.email_verification_code:
            user.is_active = True
            user.save()
            messages.success(request, 'Адрес электронной почты подтвержден')
            return redirect("login")
        else:
            messages.error(request, "Неверный код. Введите верный код.")
    return render(request, "chat/email_confirmation.html")

@login_required
def users_online(request):
    context = get_common_context(request)
    return render(request, "chat/users_online.html", context=context)

@login_required
def user_profile(request, username):
    context = get_common_context(request)
    return render(request, 'chat/user_profile.html', context=context)

@login_required
def wallet_history(request):
    transactions = Transaction.objects.filter(user = request.user)
    context = get_common_context(request)
    context.update({'transaction':transactions})
    return render(request, 'chat/wallet_history.html', context=context)

@login_required
def referrals(request):
    # Get the UserProfile instance for the currently authenticated user
    user_profile = UserProfile.objects.get(user=request.user)

    # Filter UserProfiles based on the current user as the recommender and a non-empty referral code
    referrals = UserProfile.objects.filter(recomended_by=user_profile.user)
    # Extract the usernames of the referred users using a queryset's values_list() method
    usernames = referrals.values_list('user__username', flat=True)

    home_url = reverse('home') + f'{user_profile.referal_code}'
    context = context = get_common_context(request)
    context.update({'ref_code': request.build_absolute_uri(home_url)})
    context.update({'usernames':usernames})
    return render(request, 'chat/referrals.html', context=context)

@login_required
def donate(request):
    context = get_common_context(request)
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            # Store the amount in the session
            json_data = json.dumps(amount, cls=DecimalEncoder)
            request.session['donation_amount'] = json_data
            # Create a new transaction
            transaction = Transaction(
                user=request.user,
                amount=amount,
                status='pending',
                created_at=timezone.now(),
                updated_at=timezone.now()
            )
            transaction.save()
            # Process the donation with the given amount
            # Redirect to a success page or display a success message
            return redirect('proceed_donate')
    else:
        form = DepositForm()
    context['form'] = form
    return render(request, 'chat/donate.html', context=context)

@login_required
def withdraw(request):
    context = get_common_context(request)
    if request.method == 'POST':
        form = WithdrawalForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            payeer = form.cleaned_data['payeer_account']
            # Store the amount in the session
            json_data = json.dumps(amount, cls=DecimalEncoder)
            request.session['withdrawal_amount'] = json_data
            user_profile = UserProfile.objects.get(user=request.user)
            wallet = Wallet.objects.get(user_profile=user_profile)
            if wallet.balance >= amount:
                # Create a new transaction
                transaction = Transaction(
                    user=request.user,
                    amount=amount,
                    status='pending',
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                    type='withdrawal',
                    payeer = payeer
                )
                transaction.save()
                # Process the donation with the given amount
                # Redirect to a success page or display a success message
                return redirect('proceed_withdraw')
            else:
                print('Error')
                messages.error(request, "У вас недостаточно баланса")
    else:
        form = WithdrawalForm()
    context['form'] = form
    return render(request, 'chat/withdraw.html', context=context)

@login_required
def balance(request):
    context = get_common_context(request)
    return render(request, 'chat/balance.html', context=context)

@login_required
def proceed_withdraw(request):
    context = get_common_context(request)
    return render(request, 'chat/proceed_withdraw.html', context=context)

@login_required
def proceed_donate(request):
    context = get_common_context(request)
    # Get the amount from the session
    amount = request.session.get('donation_amount')
    if not amount:
        # If the amount is not found in the session, redirect to the donate page
        return redirect('donate')
    context['amount'] = amount
    return render(request, 'chat/proceed_donate.html', context=context)

@login_required
def games(request):
    context = get_common_context(request)
    return render(request, 'chat/games.html', context=context)


@login_required
def payment_failed(request):
    context = get_common_context(request)
    return render(request, 'chat/payment_failed.html', context=context)

@login_required
def payment_success(request):
    amount = request.session.get('donation_amount')
    if not amount:
        return redirect('donate')


    user_profile = UserProfile.objects.get(user=request.user)
    wallet = Wallet.objects.select_for_update().get(user_profile=user_profile)
    wallet.balance += Decimal(amount)
    wallet.save()
    transaction = Transaction.objects.select_for_update().get(user=request.user, amount=amount, status='pending')
    transaction.status = 'completed'
    transaction.save()
    del request.session['donation_amount']
    context = get_common_context(request)
    context['amount'] = amount
    return render(request, 'chat/payment_success.html', context=context)


def users_count(request):
    online_users = User.objects.filter(userprofile__is_online=True)
    user_count = online_users.count()
    data = {'user_count': user_count}
    return JsonResponse(data)

@login_required
def bet_game(request):
    context = get_common_context(request)
    if request.method == 'POST':
        bet = Decimal(request.POST['bet'])
        user = request.user
        user_profile = UserProfile.objects.get(user=user)
        wallet = Wallet.objects.get(user_profile=user_profile)
        if wallet.balance >= bet:
            wallet.balance -= bet
            wallet.save()

            # Get the last 8 bets of the user
            last_bets = Game_Bet.objects.filter(user=user).order_by('-timestamp')[:8]

            # Check if there is an existing game that is searching for a player with the same bet
            game = Game.objects.filter(bet=bet, is_searching=True).exclude(player1=user).first()
            print("Before if " , len(last_bets))
            # Check if more than 7 of them are winning
            if len([bet for bet in last_bets if bet.is_winning]) > 7:
                print('Redirect for user', user)
                # Creating a game with an artificial opponent
                site_user = User.objects.get(username="admin")  # Site account
                game = Game.objects.create(player1=user, player2=site_user, bet=bet, is_searching=False)
                # Control the result of the game
                game.winner = site_user
                game.random_number = 1
                game.save()
                gameBet = Game_Bet.objects.create(user=user, amount=bet, current_game=game)
                return redirect('play_game')
            elif game:
                # If such a game exists, add the current user as the second player
                game.player2 = user
                game.is_searching = False
                game.save()
            else:
                # If no such game exists, create a new game with the current user as the first player
                game = Game.objects.create(player1=user, bet=bet, is_searching=True)
                game.random_number = random.randint(0,9)
                game.save()
                user_profile.is_searching_game = True
                user_profile.save()

            gameBet = Game_Bet.objects.create(user=user, amount=bet, current_game=game)
            return redirect('play_game')

        else:
            messages.error(request, "У вас недостаточно баланса")
    return render(request, 'chat/bet_game.html', context=context)




@login_required
def bet_history(request):
    context = get_common_context(request)
    bets = Game_Bet.objects.filter(user=request.user)
    print(bets)
    context['bets']=bets
    return render(request, 'chat/bet_history.html', context=context)

@login_required
def play_game(request):
    context=get_common_context(request)
    return render(request ,'chat/play_game.html', context=context)


@login_required
def chat_game(request, pk):
    context = get_common_context(request)
    game = Game.objects.filter(pk=pk).first()
    # Генерируем токены для каждого игрока
    context['game']= game
    context['email'] = request.user.email
    return render(request ,'chat/chat_game.html', context=context)

@login_required
@require_http_methods(["DELETE"])
def delete_game(request, game_id):
    game = Game.objects.filter(id=game_id).first()
    if game:
        game.delete()
        return JsonResponse({'message': 'Game deleted.'}, status=200)
    else:
        return JsonResponse({'error': 'Game not found.'}, status=404)
    
login_required
def withdrawal_requests(request):
    if request.method == 'POST':
        transaction = Transaction.objects.select_for_update().get(id=request.POST['change_status'],)
        transaction.status = request.POST['status_16']
        transaction.save()
    # Filter transactions for the current user with type of withdrawal
    transactions = Transaction.objects.filter(type=Transaction.WITHDRAWAL, status='pending')
    # Get common context if necessary
    context = get_common_context(request)
    
    # Add transactions to context
    context['transactions'] = transactions
    
    return render(request, 'chat/withdrawal_requests.html', context=context)




@login_required
def all_users(request):
    users = User.objects.all().select_related('userprofile')

    user_data = []
    for user in users:
        profile = user.userprofile
        bet_sum = Game_Bet.objects.filter(user=user, is_winning=True, is_returned=False).aggregate(Sum('amount'))['amount__sum'] or 0
        transaction_sum = Transaction.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0

        user_data.append({
            'user': user,
            'email': user.email,
            'username': user.username,
            'profile': profile,
            'bet_sum': bet_sum,
            'transaction_sum': transaction_sum
        })

    context = {'user_data': user_data}

    return render(request, 'chat/all_users.html', context=context)


def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser)
def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('all_users')
    return render(request, 'chat/confirm_delete.html', {'user': user})