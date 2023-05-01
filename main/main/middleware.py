from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection

from chat .models import Wallet

class WalletMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                request.wallet = Wallet.objects.get(user_profile=request.user.userprofile)
            except ObjectDoesNotExist:
                request.wallet = None
        else:
            request.wallet = None

        response = self.get_response(request)

        return response