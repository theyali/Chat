import json
from channels.generic.websocket import WebsocketConsumer
from .models import Game, User
from django.db.models import Q

class GameConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()
        user_profile = self.scope["user"]
        # Send initial connection message
        self.send(text_data=json.dumps({
             "type": user_profile.email
        }))

    def disconnect(self, close_code):

        super().disconnect(close_code)


    def receive(self, text_data):
        # Handle received data from the WebSocket connection
        user_profile = self.scope["user"].userprofile
        data = json.loads(text_data)
        action = data.get("action")
        self.send(text_data=json.dumps({
                    "type": user_profile,
                    
                }))
            

    def send_game_message(self, game, message):
        # Helper method to send a message to all players in the game
        players = [game.player1, game.player2]
        for player in players:
            if player and player != self.scope["user"]:
                self.send(json.dumps(message))    
