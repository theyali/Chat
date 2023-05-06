import json
import uuid
from django.shortcuts import render, redirect,  get_object_or_404 
from django.contrib import messages
from .utils import DecimalEncoder, generate_ref_code
from .models import User, UserProfile, Wallet, Transaction, Game
from django.contrib.auth import authenticate, login, logout
from .forms import MyUserCreationForm, DepositForm
from django.core.mail import send_mail
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q

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
    try:
        wallet = request.wallet
        balance = wallet.balance
    except:
        balance = ''
    return {
        'balance': balance,
    }

def home(request):
    context= get_common_context(request)
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
    return render(request, 'chat/login.html', {})

@login_required
def logout_user(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    user_profile.is_online = False
    user_profile.save()
    logout(request)
    return redirect('home')


def register_user(request):
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
            return redirect('email_confirmation')
        else:
            messages.error(request, "Произошла ошибка во время регистрации")
    return render(request, 'chat/register.html', {
        'form':form
    })

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
    transactions = Transaction.objects.all()
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
            transaction = Transaction.objects.create(
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
    with transaction.atomic():
        transaction = Transaction.objects.select_for_update().get(user=request.user, amount=amount, status='pending')
        transaction.status = 'completed'
        transaction.save()
        user_profile = UserProfile.objects.get(user=request.user)
        wallet = Wallet.objects.select_for_update().get(user_profile=user_profile)
        wallet.balance += amount
        wallet.save()
    del request.session['donation_amount']
    context = get_common_context(request)
    context['amount'] = amount
    return render(request, 'chat/payment_success.html', context=context)



@login_required
def users_count(request):
    online_users = User.objects.filter(userprofile__is_online=True)
    user_count = online_users.count()
    data = {'user_count': user_count}
    return JsonResponse(data)

@login_required
def play_game(request):
    user = request.user
    user_profile = UserProfile.objects.get(user=user)
    user_profile.is_searching_game = True
    user_profile.save()

    game = Game.objects.filter(Q(player1=user) | Q(player2=user)).first()
    if not game:
        other_profiles = UserProfile.objects.filter(is_searching_game=True).exclude(user=user)
        if other_profiles.exists():
            # Нашли других игроков - создаем игру
            other_profile = other_profiles.first()
            game = Game.objects.create(player1=user_profile.user, player2=other_profile.user, is_searching=False)
            user_profile.is_searching_game = False
            user_profile.save()
            other_profile.is_searching_game = False
            other_profile.save()
    return render(request ,'chat/play_game.html')

@login_required
def game_state(request):
    # Проверяем, есть ли текущий пользователь в игре
    game = Game.objects.filter(Q(player1=request.user) | Q(player2=request.user)).first()
    
    if game:
        return JsonResponse({
                    "is_searching": game.is_searching,
                    "player1": request.user.username,
                    "player2": ""
                })
    else:
        return JsonResponse({
            "is_searching": True,
        })
    
@login_required
def chat_game(request):
    return render(request ,'chat/chat_game.html')