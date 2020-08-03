"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
# pylint: disable=E0402, E0211
from urllib.parse import urlparse
from discord.ext import commands
from discord import Embed, DMChannel, Member, Role
from .models.core import DBError
from .models.character_model import CharacterDB, UserDB
from .models.user_model import UserDB


class InChar(commands.Cog, name='InCharacter'):
    def __init__(self, client):
        self.client = client
        self.UserDB = UserDB(client)
        self.CharacterDB = CharacterDB(client)

    def is_admin():
        async def predicate(ctx):
            return ctx.bot.user_is_admin(ctx.author)
        return commands.check(predicate)

    @commands.group(
        name='char',
        aliases=['c'],
        invoke_without_command=True,
    )
    async def char_base(self, ctx, charname=None):
        """Add/Change Characters `+help char`"""
        user_id = ctx.author.id
        user = self.UserDB.query_one(id=user_id)

        if charname is None:
            user.active_char = None
        else:
            char = self.CharacterDB.query_one(user_id=user_id, name=charname)
            if not char:
                raise commands.BadArgument(f'Character {charname} not found')
            user.active_char = char.id

        await ctx.send(f'Active Character: {charname}')

    @char_base.command(
        name='add',
    )
    async def addchar(self, ctx, charname, displayname, pic_url, npc=None):
        """Add a character"""
        valid_filetypes = ('.jpg', '.jpeg', '.png')
        parsed = urlparse(pic_url)
        if not parsed.scheme and not parsed.netloc:
            raise commands.BadArgument('Sorry - invalid picture URL')
        if not any(parsed.path.lower().endswith(filetype) for filetype in valid_filetypes):
            raise commands.BadArgument('Please only use `' + ' '.join(valid_filetypes) + '`')

        try:
            new_char = self.CharacterDB.create_new(
                user_id=ctx.author.id,
                name=charname,
                display_name=displayname,
                picture_url=pic_url,
                npc_status=True if npc else False,
            )
        except DBError as e:
            await ctx.send(e)
            return

        await ctx.send(f'Character {new_char.name} created successfully!')

    @char_base.command(
        name='edit',
        aliases=['update']
    )
    async def char_edit(self, ctx, char_name: str, attribute: str, *, value):
        if attribute.lower() in ('_id', 'rank'):
            return
        value = value.replace('`', '')
        if value.isdigit():
            value = int(value)
        char = self.CharacterDB.query_one(user_id=ctx.author.id, name=char_name)
        await char.edit(attribute, value)
        await ctx.send('Character updated')

    @char_base.command(
        name='delete',
        aliases=['del', 'remove'],
    )
    async def delete(self, ctx, charname):
        """Remove a character"""
        char = self.CharacterDB.query_one(user_id=ctx.author.id, name=charname)
        if not char:
            raise commands.BadArgument('Character not found')

        if char.delete() == 1:
            await ctx.send('Character deleted')
        else:
            raise commands.CommandError('Unexpected number of deleted rows')

    @char_base.command(
        name='alist',
    )
    @is_admin()
    async def admin_show_chars(self, ctx, target_user: Member):
        """Show all your characters"""
        user_id = target_user.id
        chars = self.CharacterDB.query_all(user_id=user_id)
        if not chars:
            raise commands.BadArgument('No characters found')

        to_print = '\n'.join(char.display_name + ' -> ' + char.name for char in chars)
        e = Embed(description='**Display Name -> name**\n\n' + to_print)
        await ctx.send(embed=e)

    @char_base.command(
        name='list',
        aliases=['ls'],
    )
    async def show_chars(self, ctx):
        """Show all your characters"""
        user_id = ctx.author.id
        user = self.UserDB.query_one(id=user_id)
        chars = self.CharacterDB.query_all(user_id=user_id)
        if not chars:
            raise commands.BadArgument('No Characters found')
        active_char = self.CharacterDB.query_one(id=user.active_char)

        list_to_print = '\n'.join(c.name + ' (NPC)' * c.npc_status for c in chars)
        pic_url = ''
        if active_char:
            list_to_print = list_to_print.replace(active_char.name, f'**{active_char.name}**', 1)
            pic_url = active_char.picture_url
        e = Embed(description=list_to_print)
        e.set_thumbnail(url=pic_url)
        await ctx.send(embed=e)

    @char_base.command(
        name='show',
    )
    async def show(self, ctx, charname=None):
        """Show the attributes of a character"""
        user_id = ctx.author.id
        if charname is None:
            user = self.UserDB.query_one(id=user_id)
            if user is None or user.active_char is None:
                raise commands.BadArgument(f'No active character found')
            char = self.CharacterDB.query_one(id=user.active_char)
        else:
            char = self.CharacterDB.query_one(user_id=user_id, name=charname)

        if not char:
            raise commands.BadArgument(f'No character with name {charname} found')

        to_print = []
        to_print.append(f'Character Information:')
        to_print.append(f'**name:** `{char.name}`')
        to_print.append(f'**display_name:** `{char.display_name}`')
        to_print.append(f'**picture_url:** `{char.picture_url}`')
        to_print.append(f'**npc_status:** `{int(char.npc_status)}`')
        char_rank = self.client.mainguild.get_role(char.rank)
        to_print.append(f'**rank:** `{char_rank.mention if char_rank else None}`')
        to_print.append(f'**level:** `{char.level}`')
        to_print.append(f'**AccountNumber:** `{char.id}`')

        await ctx.send('\n'.join(to_print))

    @commands.command(
        name='write',
        aliases=['+', 'post'],
        hidden=True,
    )
    async def write_in_character(self, ctx, charname, *, user_input=''):
        """Write a message as a specific character"""
        user_id = ctx.author.id
        user = self.UserDB.query_one(id=user_id)
        chars = self.CharacterDB.query_all(user_id=user_id)
        if not user or not chars:
            return

        selected_char = None
        for character in chars:
            if character.name.lower().startswith(charname.lower()):
                selected_char = character.id
                break
        if selected_char is None:
            # If no char is selected here - try to select the active char
            if user.active_char is None:
                return
            selected_char = user.active_char
            # If the first word was not a char name it was part of the message
            # and should be reattached to the user input
            user_input = charname + ' ' + user_input

        selected_char = self.CharacterDB.query_one(id=selected_char)
        if not selected_char:
            return

        pic_url = selected_char.picture_url
        guild_ranks = self.client.config['ranks']
        color = 0x404040
        if selected_char.rank is not None:
            color = ctx.guild.get_role(selected_char.rank).color
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

    @char_base.group(
        name='set'
    )
    @is_admin()
    async def set_base(self, ctx):
        pass

    @set_base.command(
        name='rank',
    )
    @is_admin()
    async def setrank(self, ctx, target_user: Member, charname: str, rank: Role = None):
        """Override a characters rank"""
        char = self.CharacterDB.query_one(user_id=target_user.id, name=charname)
        if not char:
            raise commands.BadArgument(f'Character not found')

        char.rank = rank.id
        await ctx.send(f'Rank override saved')

    @set_base.command(
        name='level',
    )
    @is_admin()
    async def setlevel(self, ctx, target_user: Member, charname: str, level: int):
        """Override a characters level"""
        char = self.CharacterDB.query_one(user_id=target_user.id, name=charname)
        if not char:
            raise commands.BadArgument(f'Character not found')

        char.level = level
        await ctx.send(f'Level set to {level}')


def setup(client):
    client.add_cog(InChar(client))
