from datetime import timedelta
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Game_Bet, UserProfile, Game, Wallet
import json
import random
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import render, redirect,  get_object_or_404 

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

                
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

        # handle game termination
        await self.terminate_game(self.room_name, self.scope["user"])
        # send message to other players
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'game_over',
                'message': 'Other player left the game.'
            }
        )

    ...
    # handle game_over event
    async def game_over(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Generate a random number and send it to all clients
        if message == 'start_game':
            random_number = random.randint(0, 9)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'spin_wheel',
                    'number': random_number,
                }
            )


    async def spin_wheel(self, event):
        number = event['number']

        # Send number to WebSocket
        await self.send(text_data=json.dumps({
            'number': number,
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
        return None

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        if text_data_json['type'] == 'check_game_status':
            response = await self.check_game_status()
            if response is not None:
                await self.send(text_data=json.dumps(response))



