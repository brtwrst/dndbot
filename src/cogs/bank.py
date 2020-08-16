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
from .models.user_model import UserDB

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
        self.UserDB = UserDB(client)

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
        """Get the balance of an account as a dict of currencies"""
        coins = {c: 0 for c in CURRENCIES}
        transactions = self.TransactionDB.query_all(receiver_id=account, confirmed=True)
        if not transactions:
            raise commands.BadArgument('There are no Transactions on this account yet')
        for transaction in transactions:
            for c in CURRENCIES:
                coins[c] += getattr(transaction, c) or 0
        return coins

    async def print_balance(self, ctx, account):
        """Show the balance of an account"""
        coins = self.get_balance(account)
        e = Embed()
        coins_string = [f'{v} {self.emoji[k]}' for k, v in coins.items()]
        e.add_field(name='Your Balance', value=' | '.join(coins_string))
        await ctx.send(embed=e)

    def format_transaction(self, transaction):
        """Format a Transaction for being displayed as an embed field"""
        coins = {
            c: getattr(transaction, c) if getattr(transaction, c) else 0 for c in CURRENCIES
        }
        date = transaction.date.split('.')[0].replace('T', ' ') + ' UTC'
        # user = self.client.get_user(transaction.user_id)
        # user_str = user.name + '#' + user.discriminator
        description = transaction.description
        transaction_id = transaction.id
        confirmed = transaction.confirmed
        title = f'{"(Pending) " * (not confirmed)}ID:{transaction_id} | {description}'  # - {user_str}'
        body = [f'**{coins[c]}** {self.emoji[c]} ' if coins[c] else '' for c in CURRENCIES]
        receiver = self.CharacterDB.query_one(id=transaction.receiver_id)
        if transaction.sender_id == transaction.receiver_id:
            body.append(f'\nEin/Auszahlung: {receiver.display_name}')
        else:
            sender = self.CharacterDB.query_one(id=transaction.sender_id)
            body.append(f'\nVon: {sender.display_name}')
            body.append(f'\nAn: {receiver.display_name}')
        body.append(f'\n{date}')

        return (title, ''.join(body))

    def parse_transaction_string(self, transaction_string):
        """Parse a transaction string and return a dict of coins"""
        for c in transaction_string:
            if (c not in ',+-1234567890') and (c not in CURRENCIES_SHORT):
                raise commands.BadArgument('Invalid character in transaction ' + c)

        split = transaction_string.split(',')

        coins = dict()

        for coinstring in split:
            amount = int(coinstring[:-1])
            currency = coinstring[-1:]
            if currency not in CURRENCIES_SHORT:
                raise commands.BadArgument('Invalid currency detected:' + currency)

            currency = CURRENCIES[CURRENCIES_SHORT.index(currency)]
            coins[currency] = amount

        return coins

    async def create_transaction(
        self, user_id, transaction_string, description, sender_id, receiver_id, confirm
    ):
        """Create a transaction (if money was sent create another one in the target account)

        If there is not enough money in either account -> tevert transactions and raise error"""
        if not description or not transaction_string:
            raise commands.BadArgument('Please provide a transaction string and a description')

        coins = self.parse_transaction_string(transaction_string)

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
            copper=None,
            linked=None
        )

        for currency, amount in coins.items():
            setattr(transaction, currency, amount)

        receiver_balance = self.get_balance(receiver_id)
        if any(amount < 0 for amount in receiver_balance.values()):
            await transaction.delete()
            raise commands.BadArgument('Not enough money in account')

        if sender_id != receiver_id:
            transaction2 = self.TransactionDB.create_new(
                date=datetime.now(tz=timezone.utc).isoformat(),
                user_id=user_id,
                receiver_id=sender_id,
                sender_id=receiver_id,
                description=description,
                confirmed=confirm,
                platinum=None,
                electrum=None,
                gold=None,
                silver=None,
                copper=None,
                linked=transaction.id,
            )
            for currency, amount in coins.items():
                setattr(transaction2, currency, amount*-1)

            transaction.linked = transaction2.id

        seender_balance = self.get_balance(receiver_id)
        if any(amount < 0 for amount in seender_balance.values()):
            await transaction.delete()
            raise commands.BadArgument('Not enough money in account')

        return transaction

    async def print_log(self, ctx, account):
        """Print the log for an account to a ctx"""
        e = Embed(title='Transaction Log')
        transactions = self.TransactionDB.get_history_for_account(receiver_id=account)
        if not transactions:
            raise commands.BadArgument('No Transactions')
        for transaction in transactions:
            title, body = self.format_transaction(transaction)
            e.add_field(inline=True, name=title, value=body)
        await ctx.send(embed=e)

    async def print_pending(self, ctx):
        """Print all pending transactions to a ctx"""
        e = Embed(title='Pending Transactions')
        transactions = self.TransactionDB.query_all(confirmed=0)
        if not transactions:
            raise commands.BadArgument('No Pending Transactions')
        for transaction in transactions:
            title, body = self.format_transaction(transaction)
            e.add_field(inline=False, name=title, value=body)
        await ctx.send(embed=e)

    async def confirm_transaction(self, transaction_id, check_linked=True):
        """Confirm a transaction (if money was sent confirm another one in the target account)"""
        res = ''
        transaction = self.TransactionDB.query_one(id=transaction_id)
        if not transaction:
            return f'Unknown transaction: {transaction_id}'
        if transaction.confirmed:
            return f'Transaction {transaction_id} was already confirmed'
        transaction.confirmed = True
        res = f'Confirmed transaction: {transaction_id}'
        if transaction.linked and check_linked:
            res += '\n' + await self.confirm_transaction(transaction.linked, check_linked=False)
        return res

    @commands.group(
        name='bank',
        aliases=[],
        invoke_without_command=True,
    )
    @is_admin()
    async def bank(self, ctx):
        """View and control the bank account `+help bank`"""
        await self.print_balance(ctx, account=1)

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
            sender_id=1,
            receiver_id=1,
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
    async def bank_history(self, ctx, user: Member = None, character_name=None):
        """View the bank transaction history"""
        character = None
        if user:
            if character_name:
                character = self.CharacterDB.query_one(user_id=user.id, name=character_name)
            else:
                character = self.CharacterDB.query_active_char(user_id=user.id)
        await self.print_log(ctx, character.id if character else 1)

    @bank.command(
        name='delete',
        aliases=['remove']
    )
    @is_admin()
    async def bank_delete(self, ctx, transaction_id):
        """Delete a transaction"""
        transaction = self.TransactionDB.query_one(id=transaction_id)
        if not transaction:
            raise commands.BadArgument('Unknown transaction')
        status = await transaction.delete()
        await ctx.send(f'Success - {status} transactions deleted.')

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
        if not transaction_ids:
            raise commands.BadArgument('Please specify at least one transaction id')
        for transaction_id in transaction_ids:
            result.append(await self.confirm_transaction(transaction_id))
        await ctx.send('```\n' + '\n'.join(result) + '```')

    @bank.command(
        name='transaction',
    )
    @is_admin()
    async def bank_show_transaction(self, ctx, transaction_id):
        """Display a specific transaction"""
        transaction = self.TransactionDB.query_one(id=transaction_id)
        e = Embed(title=f'Transaction {transaction_id}')
        title, body = self.format_transaction(transaction)
        e.add_field(inline=False, name=title, value=body)
        await ctx.send(embed=e)

    @bank.command(
        name='send',
    )
    async def bank_send_money(
        self, ctx, receiver_account_nr: int, transaction_string=None, *, description=None
    ):
        """Send Money to another account"""
        if receiver_account_nr == 1:
            raise commands.BadArgument('You cannot send money to yourself')

        receiver = self.CharacterDB.query_one(id=receiver_account_nr)
        if not receiver:
            raise commands.BadArgument('Receiver not found')

        transaction = await self.create_transaction(
            user_id=ctx.author.id,
            transaction_string=transaction_string,
            description=description,
            sender_id=1,
            receiver_id=receiver.id,
            confirm=True
        )
        e = Embed(
            title=f'Transaction added from Bank to {receiver.name}',
            description='\n'.join(self.format_transaction(transaction))
        )
        await ctx.send(embed=e)

    @bank.command(
        name='accounts',
    )
    @is_admin()
    async def bank_show_accounts(self, ctx):
        """Show all account holders (characters that are not NPCs)"""
        e = Embed(title='Accounts')
        users = self.UserDB.query_all()
        for user in users:
            member = self.client.get_user(user.id)
            username = member.display_name if member else 'Unknown'
            chars = self.CharacterDB.query_all(user_id=user.id)
            c_list = [
                f'{char.id}: {char.display_name} ({char.name})' for char in chars if not char.npc_status]
            if c_list:
                e.add_field(name=username, value='\n'.join(c_list), inline=True)

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
            raise commands.BadArgument('No active character found')
        await self.print_balance(ctx, character.id)

    @account.command(
        name='add',
    )
    async def account_add(self, ctx, transaction_string=None, *, description=None):
        """Add a transaction to your account `+help account add`

        The transaction_string is a comma separated list of amount and currency pairs.
        example `+account 2g,5s Pay for last mission`
        example `+account -2g,-5s Bought food for the kitchen`
        """
        character = self.CharacterDB.query_active_char(user_id=ctx.author.id)
        if not character:
            raise commands.BadArgument('No active character found')

        transaction = await self.create_transaction(
            user_id=ctx.author.id,
            transaction_string=transaction_string,
            description=description,
            sender_id=character.id,
            receiver_id=character.id,
            confirm=True
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
            raise commands.BadArgument('No active character found')
        await self.print_log(ctx, character.id)

    @account.command(
        name='delete',
        aliases=['remove']
    )
    async def account_delete(self, ctx, transaction_id):
        """Delete one of your own deposit/withdraw transactions"""
        character = self.CharacterDB.query_active_char(user_id=ctx.author.id)
        if not character:
            raise commands.BadArgument('No active character found')

        transaction = self.TransactionDB.query_one(id=transaction_id)
        if not transaction:
            raise commands.BadArgument('Unknown transaction')

        if not transaction.sender_id == transaction.receiver_id == character.id:
            raise commands.BadArgument(
                'This is not a deposit/withdraw transaction of your current character'
            )

        status = await transaction.delete()
        await ctx.send(f'Success - {status} transaction deleted.')

    @account.command(
        name='send',
    )
    async def account_send_money(
        self, ctx, receiver_account_nr: int, transaction_string=None, *, description=None
    ):
        """Send Money to another account"""
        if '-' in transaction_string:
            raise commands.BadArgument('You can only send positive amounts')

        character = self.CharacterDB.query_active_char(user_id=ctx.author.id)
        if not character:
            raise commands.BadArgument('No active character found')

        if character.id == receiver_account_nr:
            raise commands.BadArgument('You cannot send money to yourself')

        receiver = self.CharacterDB.query_one(id=receiver_account_nr)
        if not receiver:
            raise commands.BadArgument('Receiver not found')

        transaction = await self.create_transaction(
            user_id=ctx.author.id,
            transaction_string=transaction_string,
            description=description,
            sender_id=character.id,
            receiver_id=receiver.id,
            confirm=False
        )
        e = Embed(
            title=f'Transaction added from {character.name} to {receiver.name}',
            description='\n'.join(self.format_transaction(transaction))
        )
        await ctx.send(embed=e)


def setup(client):
    client.add_cog(Bank(client))
