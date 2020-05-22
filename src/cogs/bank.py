"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
#pylint: disable=E0402, E0211
import json
from urllib.parse import urlparse
from discord.ext import commands
from discord import Embed, DMChannel


class Bank(commands.Cog, name='Bank'):
    def __init__(self, client):
        self.client = client
        with open('../state/bank.json') as f:
            self.bank_history = json.load(f)

    def save_bank(self):
        with open('../state/bank.json', 'w') as f:
            json.dump(self.bank_history, f, indent=1)




def setup(client):
    client.add_cog(Bank(client))

