"""This is a cog for a discord.py bot.
It will add commands to manage a guild bank.
"""
# pylint: disable=E0402, E0211
from datetime import datetime
from discord.ext import commands
from discord.utils import get
from discord import Embed
from .utils.state_db import Transaction

CURRENCIES = ('copper', 'silver', 'electrum', 'gold', 'platinum')

class Bank(commands.Cog, name='Bank'):
    def __init__(self, client):
        self.client = client
        try:
            self.emoji = {c: get(self.client.mainguild.emojis, name=c.lower()) for c in CURRENCIES}
        except (TypeError, AttributeError):
            self.emoji = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.emoji:
            self.emoji = {c: get(self.client.mainguild.emojis, name=c.lower()) for c in CURRENCIES}

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    def get_bank_balance(self):
        coins = {c: 0 for c in CURRENCIES}
        with self.client.state.get_session() as session:
            for transaction in session.query(Transaction).all():
                for c in CURRENCIES:
                    coins[c] += amount if (amount := getattr(transaction, c)) else 0
        return coins

    async def print_balance(self, ctx):
        coins = self.get_bank_balance()
        e = Embed()
        coins_string = [f'{v}{self.emoji[k]}' for k, v in coins.items()]
        e.add_field(name='Your Balance', value=' '.join(coins_string))
        await ctx.send(embed=e)

    def format_transaction(self, transaction):
        coins = {
            c: amount if (amount := getattr(transaction, c)) else 0 for c in CURRENCIES
        }
        date = transaction.date.split('.')[0].replace('T', ' ') + ' UTC'
        user = self.client.get_user(transaction.user_id)
        user_str = user.name + '#' + user.discriminator
        description = transaction.description
        transaction_id = transaction.transaction_id
        title = f'ID:{transaction_id} | {date} - {user_str}'
        body = [f'**{coins[c]}** {self.emoji[c]} ' if coins[c] else '' for c in CURRENCIES]
        body += [f'\nZweck: {description}']
        return (title, ''.join(body))

    @commands.group(
        name='bank',
        aliases=[],
        invoke_without_command=True,
    )
    async def bank(self, ctx, transaction_string=None, *, description=None):
        """View the bank balance or add a transaction

        The transaction_string is a comma separated list of amount and currency pairs.
        example `+bank 2g,5s Donation from Dora`
        example `+bank -2g,-5s Bought food for the kitchen`
        """
        if description is None and transaction_string is None:
            await self.print_balance(ctx)
            return

        if not description or not transaction_string:
            await ctx.send('Please provide a transaction string and a description')
            return

        for c in transaction_string:
            if c not in 'csegp,+-1234567890':
                await ctx.send('Invalid character in transaction ' + c)
                return

        transaction = Transaction()
        split = transaction_string.split(',')

        for coinstring in split:
            amount = int(coinstring[:-1])
            currency = coinstring[-1:]
            if currency not in 'csegp':
                await ctx.send('Invalid currency detected:' + currency)
                return
            currency = CURRENCIES['csegp'.index(currency)]
            setattr(transaction, currency, amount)

        transaction.description = description
        transaction.user_id = ctx.author.id
        transaction.date = datetime.now().isoformat()

        with self.client.state.get_session() as session:
            session.add(transaction)

        e = Embed(
            title='Transaction Added',
            description='\n'.join(self.format_transaction(transaction))
        )
        await ctx.send(embed=e)

    @bank.command(
        name='history',
        aliases=['log'],
    )
    async def bank_history(self, ctx):
        """View the bank transaction history"""
        e = Embed(title='Transaction Log')
        with self.client.state.get_session() as session:
            for transaction in reversed(session.query(Transaction).order_by(Transaction.transaction_id.desc()).limit(10).all()):
                title, body = self.format_transaction(transaction)
                e.add_field(inline=False, name=title, value=body)
        await ctx.send(embed=e)

    @bank.command(
        name='delete',
    )
    async def bank_delete(self, ctx, transaction_id):
        """Delete a transaction"""
        with self.client.state.get_session() as session:
            session.query(Transaction).filter_by(transaction_id=transaction_id).delete()
        await ctx.send('Success')

def setup(client):
    client.add_cog(Bank(client))
