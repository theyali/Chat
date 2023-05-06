import json
from channels.generic.websocket import WebsocketConsumer
from .models import Game
from django.db.models import Q

class GameConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

        # Send initial connection message
        self.send(text_data=json.dumps({
            "type": "connection established",
            "message": "You are now connected!"
        }))

    def disconnect(self, close_code):
        # Update the user's is_searching_game field
        user_profile = self.scope["user"].userprofile
        user_profile.is_searching_game = False
        user_profile.save()

        # Check if the user is already in a game
        game = Game.objects.filter(Q(player1=self.scope["user"]) | Q(player2=self.scope["user"])).first()
        if game:
            # Remove the user from the game instance
            if game.player1 == self.scope["user"]:
                game.player1 = None
                print("Here")
            elif game.player2 == self.scope["user"]:
                game.player2 = None

            # Set the game's searching flag to True
            game.is_searching = True
            game.save()

            # Notify other players that a player has disconnected
            message = {
                "type": "player_disconnected",
                "player_username": self.scope["user"].username
            }
            self.send_game_message(game, message)

        super().disconnect(close_code)


    def receive(self, text_data):
        # Handle received data from the WebSocket connection
        data = json.loads(text_data)
        action = data.get("action")

        if action == "get_game_state":
            # Get the game state for the current user
            game = Game.objects.filter(Q(player1=self.scope["user"]) | Q(player2=self.scope["user"])).first()

            if game:
                # Send the game state to the client
                self.send(text_data=json.dumps({
                    "type": "game_state",
                    "is_searching": game.is_searching,
                    "player1": str(game.player1),
                    "player2": str(game.player2)
                }))
            else:
                # If the user is not in a game, send the searching state
                self.send(text_data=json.dumps({
                    "type": "game_state",
                    "is_searching": True
                }))
        else:
            # Handle other actions if necessary
            pass

    def send_game_message(self, game, message):
        # Helper method to send a message to all players in the game
        players = [game.player1, game.player2]
        for player in players:
            if player and player != self.scope["user"]:
                self.send(json.dumps(message))    
