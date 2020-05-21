"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
#pylint: disable=E0402
import json
import asyncio
from urllib.parse import urlparse
from discord.ext import commands
from discord import Embed, Message


class InChar(commands.Cog, name='Commands'):
    def __init__(self, client):
        self.client = client
        with open('../state/chars.json') as f:
            self.chars = json.load(f)
        self.messages = dict()

    def save_chars(self):
        with open('../state/chars.json', 'w') as f:
            json.dump(self.chars, f, indent=1)

    @commands.command(
        name='addchar',
    )
    async def addchar(self, ctx, *, charname):
        """Add a character"""
        user_id = str(ctx.author.id)
        char_list = self.chars.get(user_id, dict([('active', charname)]))
        char_list[charname] = ''
        self.chars[user_id] = char_list
        await ctx.send(f'adding {ctx.author.id}_{charname}')
        self.save_chars()

    @commands.command(
        name='deletechar',
        aliases=['delchar', 'removechar', 'remchar', 'rmchar']
    )
    async def delete(self, ctx, *, charname):
        """Remove a character"""
        user_id = str(ctx.author.id)
        char_list = self.chars.get(user_id, None)
        if char_list is None:
            return
        if charname not in char_list:
            await ctx.send(f'No character with name {charname} found')
            return
        char_list.pop(charname)
        if len(char_list) == 1:
            self.chars.pop(user_id)
        elif char_list['active'] == charname:
            char_list['active'] = list(char_list.keys())[-1]
        await ctx.send(f'removing {ctx.author.id}_{charname}')
        self.save_chars()


    @commands.command(
        name='list',
        aliases=['listchars', 'showchars', 'show']
    )
    async def show_chars(self, ctx):
        """Show all your characters"""
        user_id = str(ctx.author.id)
        char_list = self.chars.get(user_id, None)
        if not char_list:
            return
        active_char = char_list['active']
        pic_url = char_list[active_char]
        character_list = '\n'.join(cname for cname in char_list.keys() if cname != 'active')
        character_list = character_list.replace(active_char, f'**{active_char}**')
        e = Embed(description=character_list)
        e.set_thumbnail(url=pic_url)
        await ctx.send(embed=e)


    @commands.command(
        name='char',
        aliases=['active', 'activechar']
    )
    async def char(self, ctx, *, charname):
        """Select active character"""
        user_id = str(ctx.author.id)
        char_list = self.chars.get(user_id, None)
        if char_list is None:
            return
        if charname not in char_list:
            await ctx.send(f'No character with name {charname} found')
            return
        char_list['active'] = charname
        self.save_chars()
        await self.show_chars(ctx)


    @commands.command(
        name='addpic',
        aliases=['addpicture', 'pic']
    )
    async def addpic(self, ctx, *, charname):
        """Add a picture for a character"""
        user_id = str(ctx.author.id)
        char_list = self.chars.get(user_id, None)
        if char_list is None:
            return
        if charname not in char_list:
            await ctx.send(f'No character with name {charname} found')
            return
        await ctx.send('Please provide the URL of the picture')
        try:
            def check(m):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
            pic_url_message = await self.client.wait_for(
                'message',
                check=check,
                timeout=120
            )
        except asyncio.TimeoutError:
            await ctx.send(f'addpic timed out - please run the command again')
            return
        pic_url = pic_url_message.content
        parse_result = urlparse(pic_url)
        if not parse_result.scheme and not parse_result.netloc:
            await ctx.send('Sorry this does not look like a valid URL')
            return
        char_list[charname] = pic_url
        self.save_chars()
        await ctx.send(f'picture stored for {ctx.author.id}_{charname}')


    @commands.command(
        name='deletemessage',
        aliases=['del', 'delete', 'deletemsg', 'delmsg']
    )
    async def delete_message(self, ctx, msg:Message):
        """Delete one of your "In Character" messages"""
        if msg.author.id != self.client.user.id:
            return
        message_id = str(msg.id)
        if message_id not in self.messages:
            return
        requester = str(ctx.author.id)
        original_author = self.messages[message_id]
        if not requester == original_author:
            return
        self.messages.pop(message_id)
        await msg.delete()
        await ctx.message.delete()


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        user_id = str(ctx.author.id)
        char_list = self.chars.get(user_id, None)
        if char_list is None:
            return
        active_char = char_list['active']
        message_text = ctx.message.content[1:]
        pic_url = char_list[active_char]
        e = Embed(title=f'{active_char}:', description=message_text)
        e.set_thumbnail(url=pic_url)
        e.set_footer(
            text=ctx.author.display_name,
            icon_url=ctx.author.avatar_url
        )
        msg = await ctx.send(embed=e)
        self.messages[str(msg.id)] = user_id
        await ctx.message.delete()

def setup(client):
    client.add_cog(InChar(client))

