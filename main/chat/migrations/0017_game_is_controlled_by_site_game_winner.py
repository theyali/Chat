# Generated by Django 4.2 on 2023-05-16 13:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0016_game_bet_is_returned'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='is_controlled_by_site',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='game',
            name='winner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='games_won', to=settings.AUTH_USER_MODEL),
        ),
    ]
