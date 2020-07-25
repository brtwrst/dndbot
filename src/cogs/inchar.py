"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
# pylint: disable=E0402, E0211
from urllib.parse import urlparse
from discord.ext import commands
from discord import Embed, DMChannel, Member, Role
from .utils.state_db import User, Character


class InChar(commands.Cog, name='Commands'):
    def __init__(self, client):
        self.client = client

    def is_admin():
        async def predicate(ctx):
            return ctx.bot.user_is_admin(ctx.author)
        return commands.check(predicate)

    @commands.command(
        name='addchar',
        aliases=['add']
    )
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
        with self.client.state.get_session() as session:
            # Check if user exists and create entry if it does not
            if len(session.query(User).filter_by(discord_id=user_id).all()) == 0:
                user = User(discord_id=user_id, active_char=None)
                session.add(user)

            # Check if character already exists and can be modified
            res = session.query(Character).filter_by(user_id=user_id, name=charname).all()
            if res:
                newchar = res[0]
                response = 'succesfully modified'
            else:
                newchar = Character()
                response = 'succesfully added'
            newchar.name = charname
            newchar.user_id = user_id
            newchar.display_name = displayname
            newchar.picture_url = pic_url
            newchar.npc_status = True if npc else False
            session.add(newchar)
        await ctx.send(f'{charname} {response}!')

    @commands.command(
        name='deletechar',
        aliases=['delchar', 'removechar', 'remchar', 'rmchar']
    )
    async def delete(self, ctx, charname):
        """Remove a character"""
        with self.client.state.get_session() as session:
            a = session.query(Character).filter_by(user_id=ctx.author.id, name=charname).delete()
        if a:
            await ctx.send(f'{charname} successfully removed!')

    @commands.command(
        name='setrank',
    )
    @is_admin()
    async def setrank(self, ctx, target_user: Member, charname: str, rank: Role = None):
        """Override a characters rank"""

        user_id = target_user.id

        with self.client.state.get_session() as session:
            char = session.query(Character).filter_by(user_id=user_id, name=charname).first()
            if not char:
                raise commands.BadArgument('Invalid user or charactername')
            char.rank_override = rank.id if rank else None
            session.add(char)

        await ctx.send(f'Rank override saved')

    @commands.command(
        name='alist',
    )
    @is_admin()
    async def admin_show_chars(self, ctx, target_user: Member):
        """Show all your characters"""
        user_id = target_user.id
        with self.client.state.get_session() as session:
            chars = session.query(Character).filter_by(user_id=user_id).all()
            if not chars:
                raise commands.BadArgument('No characters found')

        to_print = '\n'.join(char.display_name + ' -> ' + char.name for char in chars)
        e = Embed(description='**Display Name -> name**\n\n' + to_print)
        await ctx.send(embed=e)

    @commands.command(
        name='list',
        aliases=['listchars'],
    )
    async def show_chars(self, ctx):
        """Show all your characters"""
        user_id = ctx.author.id
        with self.client.state.get_session() as session:
            char_list = session.query(Character).filter_by(user_id=user_id).all()
            active_char_id = session.query(User.active_char).filter_by(
                discord_id=user_id).first().active_char
            active_char = session.query(Character).filter_by(char_id=active_char_id).first()

        list_to_print = '\n'.join(c.name + ' (NPC)' * c.npc_status for c in char_list)
        pic_url = ''
        if active_char:
            list_to_print = list_to_print.replace(active_char.name, f'**{active_char.name}**', 1)
            pic_url = active_char.picture_url
        e = Embed(description=list_to_print)
        e.set_thumbnail(url=pic_url)
        await ctx.send(embed=e)

    @commands.command(
        name='char',
        aliases=['active', 'activechar']
    )
    async def char(self, ctx, charname=None):
        """Select active character"""
        user_id = ctx.author.id
        with self.client.state.get_session() as session:
            char = session.query(Character).filter_by(user_id=user_id, name=charname).first()
            user = session.query(User).filter_by(discord_id=user_id).first()
            if not user:
                return
            user.active_char = char.char_id if char else None
            session.add(user)
        await ctx.send(f'Active: {charname}' if user.active_char else 'No active char')

    @commands.command(
        name='show',
    )
    async def show(self, ctx, charname):
        """Select active character"""
        user_id = ctx.author.id
        with self.client.state.get_session() as session:
            char = session.query(Character).filter_by(user_id=user_id, name=charname).first()
        if not char:
            await ctx.send(f'No character with name {charname} found')
            return
        pic_url = char.picture_url
        npc = char.npc_status
        displayname = char.display_name
        await ctx.send(f'`+addchar {charname} {displayname} {pic_url} {"npc" if npc else ""}`')

    @commands.command(
        name='write',
        aliases=['+', 'post']
    )
    async def write_in_character(self, ctx, charname, *, user_input=''):
        """Write a message as a specific character"""
        user_id = ctx.author.id
        with self.client.state.get_session() as session:
            user = session.query(User).filter_by(discord_id=user_id).first()
            char_list = session.query(
                Character.name, Character.char_id).filter_by(user_id=user_id).all()
            if not user or not char_list:
                return

        selected_char = None
        for character_name, character_id in char_list:
            if character_name.lower().startswith(charname.lower()):
                selected_char = character_id
                break
        if selected_char is None:
            # If no char is selected here - try to select the active char
            if user.active_char is None:
                return
            selected_char = user.active_char
            # If the first word was not a char name it was part of the message
            # and should be reattached to the user input
            user_input = charname + ' ' + user_input
        with self.client.state.get_session() as session:
            selected_char = session.query(Character).filter_by(char_id=selected_char).first()
            if not selected_char:
                return

        pic_url = selected_char.picture_url
        guild_ranks = self.client.config['ranks']
        color = 0x404040
        if selected_char.rank_override is not None:
            color = color = ctx.guild.get_role(selected_char.rank_override).color
        elif not selected_char.npc_status and not isinstance(ctx.channel, DMChannel):
            user_roles = [role.id for role in ctx.author.roles]
            for rank in guild_ranks:
                if rank in user_roles:
                    color = ctx.guild.get_role(rank).color
                    break
        e = Embed(
            title=f'{selected_char.display_name}:',
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
