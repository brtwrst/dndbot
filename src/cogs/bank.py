"""This is a cog for a discord.py bot.
It will add commands to manage a guild bank.
"""
# pylint: disable=E0402, E0211
from datetime import datetime, timezone
from discord.ext import commands
from discord.utils import get
from discord import Embed, Member
from .models.transaction_model import TransactionDB
from .models.character_model import CharacterDB

CURRENCIES = ('platinum', 'gold', 'electrum', 'silver', 'copper')
CURRENCIES_SHORT = tuple(s[0] for s in CURRENCIES)


class Bank(commands.Cog, name='Bank'):
    def __init__(self, client):
        self.client = client
        try:
            self.emoji = {c: get(self.client.mainguild.emojis, name=c.lower())
                          or c for c in CURRENCIES}
        except (TypeError, AttributeError):
            self.emoji = None
        self.TransactionDB = TransactionDB(client)
        self.CharacterDB = CharacterDB(client)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.emoji:
            self.emoji = {c: get(self.client.mainguild.emojis, name=c.lower())
                          or c for c in CURRENCIES}

    def is_admin():
        async def predicate(ctx):
            return ctx.bot.user_is_admin(ctx.author)
        return commands.check(predicate)

    def get_balance(self, account):
        coins = {c: 0 for c in CURRENCIES}
        for transaction in self.TransactionDB.query_all(
            receiver_id=account,
            confirmed=True
        ):
            for c in CURRENCIES:
                coins[c] += getattr(transaction, c) or 0
        return coins

    async def print_balance(self, ctx, account):
        coins = self.get_balance(account)
        e = Embed()
        coins_string = [f'{v} {self.emoji[k]}' for k, v in coins.items()]
        e.add_field(name='Your Balance', value=' | '.join(coins_string))
        await ctx.send(embed=e)

    def format_transaction(self, transaction):
        coins = {
            c: getattr(transaction, c) if getattr(transaction, c) else 0 for c in CURRENCIES
        }
        date = transaction.date.split('.')[0].replace('T', ' ') + ' UTC'
        # user = self.client.get_user(transaction.user_id)
        # user_str = user.name + '#' + user.discriminator
        description = transaction.description
        transaction_id = transaction._id
        confirmed = transaction.confirmed
        title = f'{"(Pending) " * (not confirmed)}ID:{transaction_id} | {date}'#  - {user_str}'
        body = [f'**{coins[c]}** {self.emoji[c]} ' if coins[c] else '' for c in CURRENCIES]
        receiver = self.CharacterDB.query_one(_id=transaction.receiver_id)
        if transaction.sender_id == transaction.receiver_id:
            body.append(f'\nEin/Auszahlung: {receiver.display_name}')
        else:
            sender = self.CharacterDB.query_one(_id=transaction.sender_id)
            body.append(f'\nVon: {sender.display_name}')
            body.append(f'\nAn: {receiver.display_name}')
        body.append(f'\nZweck: {description}')

        return (title, ''.join(body))

    async def create_transaction(
        self, user_id, transaction_string, description, sender_id, receiver_id, confirm
    ):
        if not description or not transaction_string:
            raise commands.BadArgument('Please provide a transaction string and a description')

        for c in transaction_string:
            if (c not in ',+-1234567890') and (c not in CURRENCIES_SHORT):
                raise commands.BadArgument('Invalid character in transaction ' + c)


        transaction = self.TransactionDB.create_new(
            date=datetime.now(tz=timezone.utc).isoformat(),
            user_id=user_id,
            receiver_id=receiver_id,
            sender_id=sender_id,
            description=description,
            confirmed=confirm,
            platinum=None,
            electrum=None,
            gold=None,
            silver=None,
            copper=None
        )

        split = transaction_string.split(',')

        for coinstring in split:
            amount = int(coinstring[:-1])
            currency = coinstring[-1:]
            if currency not in CURRENCIES_SHORT:
                raise commands.BadArgument('Invalid currency detected:' + currency)

            currency = CURRENCIES[CURRENCIES_SHORT.index(currency)]
            setattr(transaction, currency, amount)

        if sender_id != receiver_id:
            transaction2 = self.TransactionDB.create_new(
                date=datetime.now(tz=timezone.utc).isoformat(),
                user_id=user_id,
                receiver_id=sender_id,
                sender_id=sender_id,
                description='AUTO GENERATED because of {transaction._id}\n' + description,
                confirmed=confirm,
                platinum=None,
                electrum=None,
                gold=None,
                silver=None,
                copper=None
            )
            for currency in CURRENCIES:
                amount = getattr(transaction, currency)
                if amount:
                    setattr(transaction2, currency, amount*-1)

        return transaction

    async def print_log(self, ctx, receiver_id):
        e = Embed(title='Transaction Log')
        transactions = self.TransactionDB.get_history_for_account(receiver_id=receiver_id)
        if not transactions:
            raise commands.BadArgument('No Transactions')
        for transaction in transactions:
            title, body = self.format_transaction(transaction)
            e.add_field(inline=False, name=title, value=body)
        await ctx.send(embed=e)

    async def print_pending(self, ctx):
        e = Embed(title='Pending Transactions')
        transactions = self.TransactionDB.query_all(confirmed=0)
        if not transactions:
            raise commands.BadArgument('No Pending Transactions')
        for transaction in transactions:
            title, body = self.format_transaction(transaction)
            e.add_field(inline=False, name=title, value=body)
        await ctx.send(embed=e)

    @commands.group(
        name='bank',
        aliases=[],
        invoke_without_command=True,
    )
    @is_admin()
    async def bank(self, ctx):
        """View and control the bank account `+help bank`"""
        await self.print_balance(ctx, 0)

    @bank.command(
        name='add',
    )
    @is_admin()
    async def bank_add(self, ctx, transaction_string=None, *, description=None):
        """Add a transaction to the bank `+help bank add`

        The transaction_string is a comma separated list of amount and currency pairs.
        example `+bank 2g,5s Donation from Dora`
        example `+bank -2g,-5s Bought food for the kitchen`
        """
        transaction = await self.create_transaction(
            user_id=ctx.author.id,
            transaction_string=transaction_string,
            description=description,
            sender_id=0,
            receiver_id=0,
            confirm=True
        )
        e = Embed(
            title=f'Transaction added to Bank',
            description='\n'.join(self.format_transaction(transaction))
        )
        await ctx.send(embed=e)

    @bank.command(
        name='history',
        aliases=['log'],
    )
    @is_admin()
    async def bank_history(self, ctx, user: Member=None, character_name=None):
        """View the bank transaction history"""
        character = None
        if user:
            if character_name:
                character = self.CharacterDB.query_one(user_id=user.id, name=character_name)
            else:
                character = self.CharacterDB.query_active_char(user_id=user.id)
        await self.print_log(ctx, character._id if character else 0)

    @bank.command(
        name='delete',
        aliases=['remove']
    )
    @is_admin()
    async def bank_delete(self, ctx, transaction_id):
        """Delete a transaction"""
        transaction = self.TransactionDB.query_one(_id=transaction_id)
        await transaction.delete()
        await ctx.send('Success')

    @bank.command(
        name='pending',
    )
    @is_admin()
    async def bank_pending(self, ctx):
        """View all pending transactions"""
        await self.print_pending(ctx)

    @bank.command(
        name='confirm',
    )
    @is_admin()
    async def bank_confirm_transaction(self, ctx, transaction_ids: commands.Greedy[int]):
        """Confirm a pending transaction"""
        result = []
        for transaction_id in transaction_ids:
            transaction = self.TransactionDB.query_one(_id=transaction_id)
            if not transaction:
                continue
            if transaction.confirmed:
                result.append(f'{transaction_id} was already confirmed')
                continue
            transaction.confirmed = True
            result.append(f'{transaction_id} confirmed')
        await ctx.send('```\n' + '\n'.join(result) + '```')

    @bank.command(
        name='transaction',
    )
    @is_admin()
    async def bank_show_transaction(self, ctx, transaction_id):
        """Display a specific transaction"""
        transaction = self.TransactionDB.query_one(_id=transaction_id)
        e = Embed(title=f'Transaction {transaction_id}')
        title, body = self.format_transaction(transaction)
        e.add_field(inline=False, name=title, value=body)
        await ctx.send(embed=e)

    @commands.group(
        name='account',
        aliases=[],
        invoke_without_command=True,
    )
    async def account(self, ctx):
        """View and control your account `+help account`"""
        character = self.CharacterDB.query_active_char(user_id=ctx.author.id)
        if not character:
            await ctx.send('No active character found')
        await self.print_balance(ctx, character._id)

    @account.command(
        name='add',
    )
    async def account_add(self, ctx, transaction_string=None, *, description=None):
        """Add a transaction to your account `+help account add`

        The transaction_string is a comma separated list of amount and currency pairs.
        example `+bank 2g,5s Pay for last mission`
        example `+bank -2g,-5s Bought food for the kitchen`
        """
        character = self.CharacterDB.query_active_char(user_id=ctx.author.id)
        if not character:
            await ctx.send('No active character found')

        transaction = await self.create_transaction(
            user_id=ctx.author.id,
            transaction_string=transaction_string,
            description=description,
            sender_id=character._id,
            receiver_id=character._id,
            confirm=False
        )
        e = Embed(
            title=f'Transaction added to account of {character.name}',
            description='\n'.join(self.format_transaction(transaction))
        )
        await ctx.send(embed=e)

    @account.command(
        name='history',
        aliases=['log'],
    )
    async def account_history(self, ctx):
        """View your account's transaction history"""
        character = self.CharacterDB.query_active_char(user_id=ctx.author.id)
        if not character:
            await ctx.send('No active character found')
        await self.print_log(ctx, character._id)

    # @account.command(
    #     name='send',
    # )
    # async def account_send_money(
    #     self, ctx, receiver: Member, transaction_string=None, *, description=None
    # ):
    #     """Send Money to another account holder"""
    #     if '-' in transaction_string:
    #         await ctx.send('You can only send positive amounts')
    #         return
    #     with self.client.state.get_session() as session:
    #         if session.query(UserData).filter_by(_id=receiver.id).count() == 0:
    #             await ctx.send('That user does not have an account')
    #             return
    #     await self.create_transaction(
    #         ctx, transaction_string, description, receiver.id, confirm=False, send=True
    #     )


def setup(client):
    client.add_cog(Bank(client))
