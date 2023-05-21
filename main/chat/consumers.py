from datetime import timedelta
import time
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Game_Bet, UserProfile, Game, Wallet
import json
from django.db.models import Q
from django.utils import timezone
from asgiref.sync import sync_to_async

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
    def update_game_result(self, game_id, winner):
        game = Game.objects.get(pk=game_id)
        loser = game.player1 if game.player1 != winner else game.player2

        # Update the game status
        game.is_searching = True
        game.winner = winner
        game.save()

        # Update the winner's balance
        winner_profile = UserProfile.objects.get(user=winner)
        winner_wallet = Wallet.objects.get(user_profile=winner_profile)
        winner_wallet.balance += game.bet * 2
        winner_wallet.save()

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
            'winner': winner.username if winner else None,
        }

        if winner:
            # Update player balance
            await self.update_player_balance(winner)

            # Announce the game result
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_result',
                    'winner': winner.username,
                }
            )

        return message

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # handle game termination
        await self.terminate_game(self.room_name, self.scope["user"])

    @sync_to_async
    def update_player_balance(self, winner):
        game = Game.objects.filter(pk=self.room_name).first() # Assumption: room_name is game id
        if game:
            profile = UserProfile.objects.get(user=winner)
            wallet = Wallet.objects.get(user_profile=profile)
            if wallet:
                wallet.balance += game.bet*2
                wallet.save()
                
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

        # Delete the game if this user is a player in the game
        game = Game.objects.filter(Q(player1=user) | Q(player2=user), is_searching=True).first()
        if game:
            game.delete()
            
        last_bet = Game_Bet.objects.filter(user=user).last()
        if not last_bet.is_returned:
            wallet = Wallet.objects.get(user_profile=profile)
            # Add the bet amount back to the user's wallet
            wallet.balance += last_bet.amount
            wallet.save()
        last_bet.delete()

    # Handle 'check_game_status' message
    @database_sync_to_async
    def check_game_status(self):
        user = self.user
        game = Game.objects.filter(Q(player1=user) | Q(player2=user), is_searching=False).first()
        if game:
            return {
                    'type': 'redirect',
                    'url': '/chat_game/',
                    'game_id':game.id
                }
        game = Game.objects.filter(Q(player1=user) | Q(player2=user)).first()
        last_bet = Game_Bet.objects.filter(user=user).last()
        if game:
            if timezone.now() - game.start_time >= timedelta(minutes=4):
                user_profile = UserProfile.objects.get(user=user)
                wallet = Wallet.objects.get(user_profile=user_profile)
                wallet.balance += game.bet
                wallet.save()
                last_bet.is_returned = True
                last_bet.save()
                game.delete()
                return {
                    'type': 'redirect',
                    'url': '/bet_game/'
                }
            elif game.player2:
                return {
                    'game_id': game.id
                }
        else:
            # Проверка количества побед пользователя
            win_count = Game.objects.filter(winner=user).count()
            if 7 <= win_count <= 15:
                # Создание игры с искусственным противником
                site_user = User.objects.get(username="admin")  # Аккаунт сайта
                new_game = Game.objects.create(player1=user, player2=site_user)
                # Управление результатом игры
                new_game.winner = site_user
                new_game.save()
                return {
                    'game_id': new_game.id
                }
        return None


    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        if text_data_json['type'] == 'check_game_status':
            response = await self.check_game_status()
            if response is not None:
                await self.send(text_data=json.dumps(response))



