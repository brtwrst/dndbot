"""This is a cog for a discord.py bot.
It will add some dice rolling commands to a bot.
"""
#pylint: disable=E0402
import json
from collections import deque
from discord.ext import commands
from discord import Embed


class Dice(commands.Cog, name='Dice'):
    def __init__(self, client):
        self.client = client
        with open('../state/aliases.json') as f:
            self.aliases = json.load(f)
        self.engine = self.client.dice_engine
        self.messages = dict()

    def save_players(self):
        with open('../state/aliases.json', 'w') as f:
            json.dump(self.aliases, f, indent=1)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            user_id = str(ctx.author.id)
            try:
                aliases = self.aliases[user_id]
            except KeyError:
                aliases = {}
            command = ctx.message.content[1:]
            if command in aliases:
                command = aliases[command]

            command = command.split(' ')
            d_command = command.pop(0)
            command = ' '.join(command)
            try:
                result = self.engine(d_command)
            except ValueError:
                return

            total = result.total
            rolls = result.rolls
            static = result.static
            success = result.success
            crithit = result.crithit
            critmiss = result.critmiss

            if success is None:
                title = None
                if crithit:
                    color = 0x00ff00
                elif critmiss:
                    color = 0xff0000
                else:
                    color = 0x000000
            else:
                title = 'Success' if success else 'Failiure'
                color = 0x00ff00 if success else 0xff0000

            rolls_str = (
                '(' + ' + '.join(map(str, rolls)) + ')') if rolls else ''
            rolls_str = rolls_str.replace('-', '- ')
            if static and rolls:
                static_str = ' + ' + str(static).replace('-', '- ')
            else:
                static_str = ''
            e = Embed(
                title=title,
                description='*' + d_command + (f' ({command})*' if command else '*') +
                ('\n' if rolls_str else '') +
                (rolls_str + static_str).replace('+ -', '-') +
                f' = **{total}**',
                color=color,
            )
            e.set_footer(
                text=ctx.author.display_name,
                icon_url=ctx.author.avatar_url
            )
            msg = await ctx.send(embed=e)
            if user_id not in self.messages:
                self.messages[user_id] = deque()
            self.messages[user_id].append(msg)
            await ctx.message.delete()

    @commands.command(
        name='alias',
        aliases=['a'],
    )
    async def alias(self, ctx, alias_name: str, *, alias_text=None):
        """Create an alias.

        Examples:
         - `!a init d20+2 Initiative`
         - `!a bh 4d6 Burning Hands`
         - `!a ebh d10+d6+4 Eldritch Bolt + Hex`
        """
        user_id = str(ctx.author.id)
        if user_id not in self.aliases:
            self.aliases[user_id] = {
                'death': 'd10=10 death save'
            }
        if not alias_text:
            if alias_name in self.aliases[user_id]:
                del self.aliases[user_id][alias_name]
                # await ctx.send('Alias deleted')
        else:
            self.aliases[user_id][alias_name] = alias_text
            # await ctx.send('Alias saved')
        self.save_players()
        await ctx.message.delete()

    @commands.command(
        name='list',
        aliases=['l'],
    )
    async def list(self, ctx):
        """List your aliases."""
        user_id = str(ctx.author.id)
        if user_id not in self.aliases:
            return
        alias_list = []
        for k, v in self.aliases[user_id].items():
            alias_list.append(f'{k} -> {v}')
        e = Embed(
            description='\n'.join(alias_list)
        )
        e.set_footer(
            text=ctx.author.display_name,
            icon_url=ctx.author.avatar_url
        )
        msg = await ctx.send(embed=e)
        await msg.add_reaction('❌')
        await ctx.message.delete()

    @commands.command(
        name='delete',
        aliases=['del'],
        hidden=True
    )
    async def delete_msg(self, ctx, num: int = 1):
        """Delete the last [num] dice-roll messages caused by the caller"""
        user_id = str(ctx.author.id)
        if user_id in self.messages:
            msg_stack = self.messages[user_id]
            for _ in range(num):
                msg = msg_stack.pop()
                await msg.delete()
                if not msg_stack:
                    del self.messages[user_id]
                    break
        await ctx.message.delete()

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        msg = reaction.message
        try:
            orig_user = msg.embeds[0].footer.text
        except:
            return
        if not user.display_name == orig_user:
            return
        if reaction.emoji == '❌':
            await msg.delete()


def setup(client):
    client.add_cog(Dice(client))
