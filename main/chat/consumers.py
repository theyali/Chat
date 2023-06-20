from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Game_Bet, UserProfile, Game, Wallet, Game_Bet
import json
from django.db.models import Q
from django.utils import timezone
from django.db import transaction
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import get_user_model
import json
import asyncio

class GameConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['pk']
        self.room_group_name = f'game_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    @database_sync_to_async
    @transaction.atomic
    def update_game_result(self, game_id, winner):
        game = Game.objects.select_for_update().get(pk=game_id)
        
        if game.winner is not None:
            # If the game result has already been processed, skip the processing
            return

        loser = game.player1 if game.player1 != winner else game.player2

        # Update the game status
        game.is_searching = True
        game.winner = winner
        game.save()

        # Update the winner's balance
        winner_profile = UserProfile.objects.get(user=winner)
        winner_wallet = Wallet.objects.select_for_update().get(user_profile=winner_profile)
        winner_wallet.balance += game.bet * 2
        winner_wallet.save()

        # Update game_bet.is_winning for the winner
        game_bet = Game_Bet.objects.get(current_game=game, user=winner)
        game_bet.is_winning = True
        game_bet.save()

        # Set the players to searching mode
        winner_profile.is_searching_game = True
        winner_profile.save()
        loser_profile = UserProfile.objects.get(user=loser)
        loser_profile.is_searching_game = True
        loser_profile.save()

    @database_sync_to_async
    def get_game(self, game_id):
        game = Game.objects.filter(pk=game_id).select_related('player1', 'player2').first()
        return game


    
    async def spin_wheel(self, event):
        number = event['number']
       
        game = await self.get_game(self.room_name)
        
        if game is None:
                return
        player1 = game.player1
        player2 = game.player2
        # Determine the winner based on the number
        # Assume that 'player1' and 'player2' are User objects or have similar structure

        winner = player1 if number % 2 == 0 else player2
        if winner:
            await self.update_game_result(self.room_name, winner)

        # Return the message instead of sending it
        message = {
            'number': number,
            'winner': winner.email if winner else None,
        }

        return message

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # handle game termination
        await self.terminate_game(self.room_name, self.scope["user"])
                
    @database_sync_to_async
    def terminate_game(self, game_id, user):
        game = Game.objects.filter(pk=game_id).first()
        if game:
            if game.player1 == user:
                if game.player2:
                    # If the game has a second player, make them the first player
                    game.player1 = game.player2
                    game.player2 = None
            elif game.player2 == user:
                # If the second player is the one leaving, just set player2 to None
                game.player2 = None

            game.is_searching = True
            game.save()

            # Set the remaining player to searching mode
            remaining_player = game.player1
            remaining_profile = UserProfile.objects.get(user=remaining_player)
            remaining_profile.is_searching_game = True
            remaining_profile.save()

                
    # handle game_over event
    async def game_over(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def game_result(self, event):
        winner = event['winner']

    @database_sync_to_async
    def get_game_random_number(self, game_id):
        game = Game.objects.get(pk=game_id)
        return game.random_number

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Use the random number from the game instance
        if message == 'start_game':
            random_number = await self.get_game_random_number(self.room_name)
            spin_wheel_result = await self.spin_wheel({
                'number': random_number,
            })
            # Send the spin_wheel_result back to the client
            await self.send(text_data=json.dumps(spin_wheel_result))
        if message == 'game over':
            print(message)
            self.send(text_data=json.dumps({
                'message': 'Game over. You will be redirected.'
            }))



class SearchGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        await self.accept()

    async def disconnect(self, close_code):
        # stop searching game when user leaves the page
        await self.stop_searching_game(self.user)

    @database_sync_to_async
    def stop_searching_game(self, user):
        profile = UserProfile.objects.get(user=user)
        profile.is_searching_game = False
        profile.save()

        # Delete the game if this user is a player in the game and the game is still searching for another player
        game = Game.objects.filter(Q(player1=user) | Q(player2=user)).first()
        if game:
            if game.is_searching:  
                game.delete()
                
                last_bet = Game_Bet.objects.filter(user=user).last()
                if not last_bet.is_returned:
                    wallet = Wallet.objects.get(user_profile=profile)
                    # Add the bet amount back to the user's wallet
                    wallet.balance += last_bet.amount
                    wallet.save()
                last_bet.delete()


    @database_sync_to_async
    def check_game_status(self):
        user = self.user
        game = Game.objects.filter(Q(player1=user) | Q(player2=user)).first()
        if game:
            if not game.is_searching:
                # If the game is found, redirect the user, and do not return the bet
                return {
                    'type': 'redirect',
                    'url': '/chat_game/',
                    'game_id': game.id
                }
            elif timezone.now() - game.start_time >= timedelta(minutes=4):
                # If the game wait time exceeds 4 minutes, return the bet
                user_profile = UserProfile.objects.get(user=user)
                wallet = Wallet.objects.get(user_profile=user_profile)
                wallet.balance += game.bet
                wallet.save()
                last_bet = Game_Bet.objects.filter(user=user).last()
                last_bet.is_returned = True
                last_bet.save()
                game.delete()
                return {
                    'type': 'redirect',
                    'url': '/bet_game/'
                }
        return None

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        if text_data_json['type'] == 'check_game_status':
            response = await self.check_game_status()
            if response is not None:
                await self.send(text_data=json.dumps(response))




User = get_user_model()

class CommonConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope["user"]
        self.last_ping = None
        await self.accept()
        # start a background task that checks for inactivity
        self.check_activity_task = asyncio.create_task(self.check_activity())

    async def disconnect(self, close_code):
        # cancel the background task on disconnect
        self.check_activity_task.cancel()

    async def receive(self, text_data):
        # when receiving a 'ping' message, update the last ping time
        text_data_json = json.loads(text_data)
        if text_data_json.get('type') == 'ping':
            self.last_ping = asyncio.get_running_loop().time()
            print('Received ping at: ', self.last_ping)

    @database_sync_to_async
    def logout_user(self):
        # remove session key for this user to logout
        session_key = self.scope["session"].session_key
        session = SessionStore(session_key=session_key)
        session.flush()

    @database_sync_to_async
    def set_user_offline(self, user):
        user_profile = UserProfile.objects.get(user=user)
        user_profile.is_online = False
        user_profile.save()

    async def check_activity(self):
        while True:
            print('Checking activity...')
            if self.last_ping is not None:
                print('Last ping received at: ', self.last_ping)
                time_diff = asyncio.get_running_loop().time() - self.last_ping
                print('Time difference: ', time_diff)
                if time_diff > 120:  # 120 seconds = 2 minutes
                    # if the user has not sent a 'ping' in the last 2 minutes, log them out
                    await self.set_user_offline(self.user)
                    print('user is logged out')
                    await self.logout_user()
                    await self.close()
                    break
            await asyncio.sleep(10)