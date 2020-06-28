"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
# pylint: disable=E0402, E0211
import json
from urllib.parse import urlparse
from discord.ext import commands
from discord import Embed, DMChannel, Member, Role


class InChar(commands.Cog, name='Commands'):
    def __init__(self, client):
        self.client = client
        with open('../state/users.json') as f:
            self.users = json.load(f)
        self.users = {int(k): v for k, v in self.users.items()}

    def save_users(self):
        with open('../state/users.json', 'w') as f:
            json.dump(self.users, f, indent=1)

    def is_dm_chat():
        async def predicate(ctx):
            return isinstance(ctx.channel, DMChannel)
        return commands.check(predicate)

    def is_admin():
        async def predicate(ctx):
            return ctx.bot.user_is_admin(ctx.author)
        return commands.check(predicate)

    @commands.command(
        name='addchar',
        aliases=['add']
    )
    @is_dm_chat()
    async def addchar(self, ctx, charname, displayname, pic_url, npc=None):
        """Add a character"""
        valid_filetypes = ('.jpg', '.jpeg', '.png')
        parsed = urlparse(pic_url)
        if not parsed.scheme and not parsed.netloc:
            await ctx.send('Sorry - invalid picture URL')
            return
        if not any(parsed.path.lower().endswith(filetype) for filetype in valid_filetypes):
            await ctx.send('Please only use `' + ' '.join(valid_filetypes) + '`')
            return
        user_id = ctx.author.id
        user = self.users.get(user_id, {'characters': dict(), 'active': charname})
        user['characters'][charname] = {
            'picture': pic_url,
            'npc': True if npc else False,
            'displayname': displayname
        }
        self.users[user_id] = user
        await ctx.send(f'{charname} succesfully added!')
        self.save_users()

    @commands.command(
        name='deletechar',
        aliases=['delchar', 'removechar', 'remchar', 'rmchar']
    )
    @is_dm_chat()
    async def delete(self, ctx, charname):
        """Remove a character"""
        user_id = ctx.author.id
        if user_id not in self.users:
            return
        user = self.users[user_id]
        char_list = user['characters']
        if charname not in char_list:
            await ctx.send(f'No character with name {charname} found')
            return
        if user['active'] == charname:
            user['active'] = None
        char_list.pop(charname)
        if len(char_list) == 0:
            self.users.pop(user_id)
        await ctx.send(f'{charname} successfully removed!')
        self.save_users()

    @commands.command(
        name='setrank',
    )
    @is_admin()
    async def setrank(self, ctx, target_user:Member, charname:str, rank:Role=None):
        """Override a characters rank"""

        user_id = target_user.id

        user = self.users.get(user_id, None)
        if user is None:
            raise commands.BadArgument('User does not have any characters')

        if charname not in user['characters']:
            raise commands.BadArgument('User does not have a character with that name')

        if rank is None:
            user['characters'][charname].pop('rank_override', None)
        else:
            user['characters'][charname]['rank_override'] = rank.id

        self.users[user_id] = user
        await ctx.send(f'Success')
        self.save_users()

    @commands.command(
        name='list',
        aliases=['listchars']
    )
    @is_dm_chat()
    async def show_chars(self, ctx):
        """Show all your characters"""
        user_id = ctx.author.id
        if user_id not in self.users:
            return
        user = self.users[user_id]
        char_list = user['characters']
        active_char = user['active']
        list_to_print = '\n'.join(c + ' (NPC)' * char_list[c]['npc'] for c in char_list.keys())
        pic_url = ''
        if active_char:
            list_to_print = list_to_print.replace(active_char, f'**{active_char}**', 1)
            pic_url = char_list[active_char]['picture']
        e = Embed(description=list_to_print)
        e.set_thumbnail(url=pic_url)
        await ctx.send(embed=e)

    @commands.command(
        name='char',
        aliases=['active', 'activechar']
    )
    @is_dm_chat()
    async def char(self, ctx, charname=None):
        """Select active character"""
        user_id = ctx.author.id
        if user_id not in self.users:
            return
        user = self.users[user_id]
        char_list = user['characters']
        if charname not in char_list and charname is not None:
            await ctx.send(f'No character with name {charname} found')
            return
        user['active'] = charname
        await ctx.send(f'Active character: {charname}')
        self.save_users()

    @commands.command(
        name='show',
    )
    @is_dm_chat()
    async def show(self, ctx, charname):
        """Select active character"""
        user_id = ctx.author.id
        if user_id not in self.users:
            return
        user = self.users[user_id]
        char_list = user['characters']
        if charname not in char_list:
            await ctx.send(f'No character with name {charname} found')
            return
        pic_url = char_list[charname]['picture']
        npc = char_list[charname]['npc']
        await ctx.send(f'`+addchar {charname} {pic_url} {"npc" if npc else ""}`')

    @commands.command(
        name='+'
    )
    async def write_in_character(self, ctx, charname, *, user_input=''):
        """Write a message as a specific character"""
        user_id = ctx.author.id
        if user_id not in self.users:
            return
        user = self.users[user_id]
        char_list = user['characters']
        selected_char = None
        for character_name in char_list.keys():
            if character_name.lower().startswith(charname.lower()):
                selected_char = character_name
                break
        if selected_char is None:
            if user['active'] is None:
                return
            selected_char = user['active']
            user_input = charname + ' ' + user_input
        pic_url = char_list[selected_char]['picture']
        guild_ranks = self.client.config['ranks']
        color = 0x404040
        if 'rank_override' in char_list[selected_char]:
            color = color = ctx.guild.get_role(char_list[selected_char]['rank_override']).color
        elif not char_list[selected_char]['npc'] and not isinstance(ctx.channel, DMChannel):
            user_roles = [role.id for role in ctx.author.roles]
            for rank in guild_ranks:
                if rank in user_roles:
                    color = ctx.guild.get_role(rank).color
        e = Embed(
            title=f'{char_list[selected_char]["displayname"]}:',
            description=user_input,
            color=color
        )
        e.set_thumbnail(url=pic_url)
        e.set_footer(
            text='@' + ctx.author.name  # +'#'+ctx.author.discriminator,
            # icon_url=ctx.author.avatar_url
        )
        await ctx.send(embed=e)
        if not isinstance(ctx.channel, DMChannel):
            await ctx.message.delete()


def setup(client):
    client.add_cog(InChar(client))
