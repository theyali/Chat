# Generated by Django 4.2 on 2023-05-16 12:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0015_remove_game_bet_game_game_bet_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='game_bet',
            name='is_returned',
            field=models.BooleanField(default=False),
        ),
    ]