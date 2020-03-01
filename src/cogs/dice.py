"""This is a cog for a discord.py bot.
It will add some dice rolling commands to a bot.
"""

import json
from random import randint
from collections import deque
from discord.ext import commands
from discord import Embed


#pylint: disable=E1101

class DiceEngine():
    def __init__(self):
        pass

    @staticmethod
    def split(arg: str):
        splits = []
        if arg[0] not in '+-':
            arg = '+' + arg
        current = []
        for c in arg:
            if c in '+-' and current:
                splits.append(''.join(current))
                current = [c]
            else:
                current.append(c)
        res = splits + [''.join(current)]
        return res

    def __call__(self, arg):
        arg = arg.lower()
        if any(x not in 'd+-0123456789' for x in arg):
            raise ValueError('invalid dice-roll string ' + arg)
        static = 0
        rolls = []
        for group in self.split(arg):
            mul = int(group[0] + '1')
            group = group[1:]
            if not 'd' in group:
                static += int(group) * mul
                continue
            num_dice, dice_type = group.split('d')
            num_dice = 1 if not num_dice else int(num_dice)
            dice_type = int(dice_type)
            [rolls.append(randint(1, dice_type) * mul)
             for _ in range(num_dice)]
        return (static + sum(rolls), rolls, static)


class Dice(commands.Cog, name='Configure aliases'):
    def __init__(self, client):
        self.client = client
        with open('../aliases.json') as f:
            self.aliases = json.load(f)
        self.engine = DiceEngine()
        self.messages = dict()

    def save_players(self):
        with open('../aliases.json', 'w') as f:
            json.dump(self.aliases, f)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            user_id = str(ctx.author.id)
            aliases = self.aliases[user_id]
            command = ctx.message.content[1:]
            if command in aliases:
                command = aliases[command]

            command = command.split(' ')
            d_command = command.pop(0)
            command = ' '.join(command)
            try:
                total, rolls, static = self.engine(d_command)
            except ValueError as error:
                return
            rolls_str = ('(' + ' + '.join(map(str, rolls)) + ')') if rolls else ''
            rolls_str = rolls_str.replace('-', '- ')
            if static and rolls:
                static_str = ' + ' + str(static).replace('-', '- ')
            else:
                static_str = ''
            e = Embed(
                description = '*' + d_command + (f' ({command})*' if command else '*') +
                ('\n' if rolls_str else '') +
                (rolls_str + static_str).replace('+ -', '-') + f' = **{total}**',
            )
            e.set_footer(
                text=ctx.author.display_name,
                icon_url=ctx.author.avatar_url
            )
            msg = await ctx.send(embed=e)
            if user_id not in self.messages:
                self.messages[user_id] = deque()
            self.messages[user_id].append(msg)
            print(self.messages)
            await ctx.message.delete()

    @commands.command(
        name='alias',
        aliases=['a'],
        hidden=True
    )
    async def alias(self, ctx, alias_name: str, *, alias_text=None):
        """You can create an alias by typing `!a [alias name] [alias command]`.
        Examples:
         - `!a init d20+2 Initiative`
         - `!a bh 4d6 Burning Hands`

        You can use an alias by typing `![alias name]`
        Examples:
         - `!init`
         - `!bh`

        You can delete an alias by typing `!a [alias name]` without a command.
        Examples:
         - `!a init`
         - `!a bh`

        You can list your current aliases by typing `!list` or `!l`

        Aliases are saved on a per user basis."""
        user_id = str(ctx.author.id)
        if user_id not in self.aliases:
            self.aliases[user_id] = {}
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
        hidden=True
    )
    async def list(self, ctx):
        """List your aliases.

        You can create aliases by using the `!alias` or `!a` command."""
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
    async def delete_msg(self, ctx):
        """Delete the last bot message caused by the caller"""
        user_id = str(ctx.author.id)
        if user_id in self.messages:
            msg_stack = self.messages[user_id]
            msg = msg_stack.pop()
            await msg.delete()
            if not msg_stack:
                del self.messages[user_id]
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
