from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import UserProfile, Game
import json
import random

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
            if game.player1 == user or game.player2 == user:
                game.delete()
                # Set the other player to searching mode
                other_player = game.player2 if game.player1 == user else game.player1
                other_profile = UserProfile.objects.get(user=other_player)
                other_profile.is_searching_game = True
                other_profile.save()
                
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