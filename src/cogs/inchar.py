"""This is a cog for a discord.py bot.
It will add commands to speak in character.
"""
#pylint: disable=E0402, E0211
import json
from urllib.parse import urlparse
from discord.ext import commands
from discord import Embed, Message, DMChannel


class InChar(commands.Cog, name='Commands'):
    def __init__(self, client):
        self.client = client
        with open('../state/users.json') as f:
            self.users = json.load(f)
        self.users = {int(k):v for k,v in self.users.items()}
        self.messages = dict()

    def save_users(self):
        with open('../state/users.json', 'w') as f:
            json.dump(self.users, f, indent=1)

    def is_dm_chat():
        async def predicate(ctx):
             return isinstance(ctx.channel, DMChannel)
        return commands.check(predicate)

    @commands.command(
        name='addchar',
        aliases=['add']
    )
    @is_dm_chat()
    async def addchar(self, ctx, charname, pic_url, npc=None):
        """Add a character"""
        user_id = ctx.author.id
        user = self.users.get(user_id, {'characters': dict(), 'active': charname})
        user['characters'][charname] = {'picture': pic_url, 'npc':True if npc else False}
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
        char_list.pop(charname)
        if len(char_list) == 0:
            self.users.pop(user_id)
        await ctx.send(f'{charname} successfully removed!')
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
        list_to_print = '\n'.join(cname for cname in char_list.keys())
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
        user['active'] = charname
        await ctx.send(f'Active character: {charname}')
        self.save_users()

    @commands.command(
        name='show',
    )
    @is_dm_chat()
    async def show(self, ctx, charname=None):
        """Select active character"""
        user_id = ctx.author.id
        if user_id not in self.users:
            return
        user = self.users[user_id]
        char_list = user['characters']
        if charname not in char_list and charname is not None:
            await ctx.send(f'No character with name {charname} found')
        pic_url = char_list[charname]['picture']
        npc = char_list[charname]['npc']
        await ctx.send(f'`+addchar {charname} {pic_url} {"npc" if npc else ""}`')

    # @commands.command(
    #     name='deletemessage',
    #     aliases=['del', 'delete', 'deletemsg', 'delmsg']
    # )
    # async def delete_message(self, ctx, msg:Message):
    #     """Delete one of your "In Character" messages"""
    #     if msg.author.id != self.client.user.id:
    #         return
    #     message_id = str(msg.id)
    #     if message_id not in self.messages:
    #         return
    #     requester = str(ctx.author.id)
    #     original_author = self.messages[message_id]
    #     if not requester == original_author:
    #         return
    #     self.messages.pop(message_id)
    #     await msg.delete()
    #     await ctx.message.delete()

    @commands.command(
        name='+',
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
        e = Embed(
            title=f'{selected_char}:',
            description=user_input,
            color=ctx.author.color
        )
        e.set_thumbnail(url=pic_url)
        e.set_footer(
            text='@' + ctx.author.name#+'#'+ctx.author.discriminator,
            # icon_url=ctx.author.avatar_url
        )
        msg = await ctx.send(embed=e)
        self.messages[msg.id] = user_id
        await ctx.message.delete()


def setup(client):
    client.add_cog(InChar(client))

