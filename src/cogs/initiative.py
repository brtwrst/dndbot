"""This is a cog for a discord.py bot.
It will add some dice rolling commands to a bot.
"""
#pylint: disable=E0402

import json
from discord import Embed
from discord.ext import commands


class Initiative(commands.Cog, name='Initiative'):
    def __init__(self, client):
        self.client = client
        self.engine = self.client.dice_engine
        self.initiatives = dict()
        self.last_initiative_message = None

    async def print_initiative(self, ctx):
        if not self.initiatives:
            await ctx.message.delete()
            return
        sorted_init = sorted(self.initiatives.items(),
                             key=lambda x: x[1], reverse=True)
        description = []
        for k, v in sorted_init:
            description.append(f'{v} | {k}')
        e = Embed(title='Initiative Order', description='\n'.join(description))
        if self.last_initiative_message:
            await self.last_initiative_message.delete()
        await ctx.message.delete()
        self.last_initiative_message = await ctx.send(embed=e)

    async def clear_initiative(self, ctx):
        self.initiatives.clear()
        if self.last_initiative_message:
            await self.last_initiative_message.delete()
        await ctx.message.delete()
        self.last_initiative_message = None

    @commands.command(
        name='inita',
        aliases=['initadd', 'Inita', 'Initadd'],
    )
    async def add_init(self, ctx, value: str = None, *, name: str = None):
        """Add to the initiative tracker"""
        try:
            if value is None:
                user_id = str(ctx.author.id)
                with open('../state/aliases.json') as f:
                    aliases = json.load(f)[user_id]

                for alias_name in ('init', 'initiative', 'Init', 'Initiative'):
                    if alias_name in aliases:
                        value = aliases[alias_name].split(' ')[0]
        except KeyError:
            await ctx.send('No `init` alias found. Create one by typing `!a init [init_roll]`')
            return

        try:
            result = self.engine(value)
        except ValueError as e:
            await ctx.send('Error in command `initadd`: ' + str(e))
            return

        total = result.total

        if name is None:
            name = ctx.author.display_name
        if name in self.initiatives:
            del self.initiatives[name]
        self.initiatives[name] = total
        await self.print_initiative(ctx)

    @commands.command(
        name='initd',
        aliases=['initdel', 'Initd', 'Initdel'],
    )
    async def del_init(self, ctx, *, name: str = None):
        """Clear/Delete from the initiative tracker"""
        if name is None:
            await self.clear_initiative(ctx)
            return
        for k in self.initiatives.keys():
            if name.lower() in k.lower():
                del self.initiatives[k]
                break
        await self.print_initiative(ctx)

    @commands.command(
        name='inits',
        aliases=['initsh', 'initshow', 'Inits', 'Initsh', 'Initshow'],
    )
    async def show_init(self, ctx):
        """Show the initiative tracker"""
        await self.print_initiative(ctx)


def setup(client):
    client.add_cog(Initiative(client))
