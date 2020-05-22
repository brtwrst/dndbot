"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
# pylint: disable=E0402, E0211
import json
from datetime import datetime
from discord.ext import commands
from discord.utils import get
from discord import Embed

CURRENCIES = ('Copper', 'Silver', 'Electrum', 'Gold', 'Platinum')


class Bank(commands.Cog, name='Bank'):
    def __init__(self, client):
        self.client = client
        self.main_guild = self.client.get_guild(525426489366282248)
        with open('../state/bank.json') as f:
            self.transaction_history = json.load(f)
        self.emoji = {c: get(self.main_guild.emojis, name=c.lower()) for c in CURRENCIES}

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    def get_bank_coins(self):
        coins = {c: 0 for c in CURRENCIES}
        for transaction in self.transaction_history:
            for c in CURRENCIES:
                coins[c] += transaction.get(c, 0)
        return coins

    async def print_bank(self, ctx):
        coins = self.get_bank_coins()
        e = Embed()
        coins_string = [f'{v}{self.emoji[k]}' for k, v in coins.items()]
        e.add_field(name='Your Balance', value=' '.join(coins_string))
        await ctx.send(embed=e)

    async def process_transaction(self, transaction):
        self.transaction_history.append(transaction)
        self.save_transaction_history()
        return True

    def format_transaction(self, transaction):
        coins = {
            c: transaction.get(c, 0) for c in CURRENCIES
        }
        date = transaction['date'].split('.')[0].replace('T', ' ')
        user = transaction['user']
        description = transaction['description']
        title = f'{date} - {user}'
        body = [f'**{coins[c]}** {self.emoji[c]} ' if coins[c] else '' for c in CURRENCIES]
        body += [f'\nZweck: {description}']
        return (title, ''.join(body))

    def save_transaction_history(self):
        with open('../state/bank.json', 'w') as f:
            json.dump(self.transaction_history, f, indent=1)

    @commands.command(
        name='bank',
        aliases=[],
    )
    async def bank(self, ctx, transaction_string=None, *, description=None):
        """View the bank balance or add a transaction

        The transaction_string is a comma separated list of amount and currency pairs.
        example `+bank 2g,5s Donation from Dora`
        example `+bank -2g,-5s Bought food for the kitchen`
        """
        if description is None and transaction_string is None:
            await self.print_bank(ctx)
            return

        if not description or not transaction_string:
            await ctx.send('Please provide a transaction string and a description')
            return

        for c in transaction_string:
            if c not in 'csegp,+-1234567890':
                await ctx.send('Invalid character in transaction ' + c)
                return

        transaction = dict()
        split = transaction_string.split(',')

        for coinstring in split:
            amount = int(coinstring[:-1])
            currency = coinstring[-1:]
            if currency not in 'csegp':
                await ctx.send('Invalid currency detected:' + currency)
                return
            currency = CURRENCIES['csegp'.index(currency)]
            transaction[currency] = amount

        transaction['description'] = description
        transaction['user'] = ctx.author.name + '#' + ctx.author.discriminator
        transaction['date'] = datetime.now().isoformat()

        if not await self.process_transaction(transaction):
            await ctx.send('Error processing transaction')
            return

        e = Embed(
            title='Transaction Added',
            description='\n'.join(self.format_transaction(transaction))
        )
        await ctx.send(embed=e)

    @commands.command(
        name='history',
        aliases=['bank_log', 'bank_history']
    )
    async def bank_history(self, ctx):
        """View the bank transaction history"""
        e = Embed(title='Transaction Log')
        for transaction in self.transaction_history[max(-10, -1*len(self.transaction_history)):]:
            title, body = self.format_transaction(transaction)
            e.add_field(inline=False, name=title, value=body)
        await ctx.send(embed=e)


def setup(client):
    client.add_cog(Bank(client))
