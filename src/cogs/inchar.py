"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
#pylint: disable=E0402
import json
from discord.ext import commands
from discord import Embed


class InChar(commands.Cog, name='InChar'):
    def __init__(self, client):
        self.client = client


def setup(client):
    client.add_cog(InChar(client))
