"""This is a cog for a discord.py bot.
It will add some dice rolling commands to a bot.
"""

from discord import Embed
from discord.ext import commands

#pylint: disable=E1101


class Initiative(commands.Cog, name='Initiative'):
    def __init__(self, client):
        self.client = client
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
        name='addi',
        aliases=['ai'],
        # hidden=True
    )
    async def add_init(self, ctx, value: int, *, name:str = None):
        """Add to the initiative list `!addi [value] [name]`"""
        if name is None:
            name = ctx.author.display_name
        if name in self.initiatives:
            del self.initiatives[name]
        self.initiatives[name] = value
        await self.print_initiative(ctx)

    @commands.command(
        name='deli',
        aliases=['di'],
        # hidden=True
    )
    async def del_init(self, ctx, *, name: str=None):
        """Delete from the initiative list `!deli [name]`"""
        if name is None:
            await self.clear_initiative(ctx)
            return
        for k in self.initiatives.keys():
            if name.lower() in k.lower():
                del self.initiatives[k]
                break
        await self.print_initiative(ctx)

    @commands.command(
        name='showi',
        aliases=['si'],
        # hidden=True
    )
    async def show_init(self, ctx):
        """Show the initiative list"""
        await self.print_initiative(ctx)


def setup(client):
    client.add_cog(Initiative(client))
