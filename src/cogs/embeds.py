"""This is a cog for a discord.py bot.
It will add commands to manage embeds.
"""
# pylint: disable=E0402, E0211
import json
from io import BytesIO
from datetime import datetime, timezone
from discord.ext import commands
from discord.errors import NotFound
from discord import Embed, TextChannel, File
from .utils.state_db import EmbedData


class EmbedController(commands.Cog, name='EmbedController'):
    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    async def post_embed(self, embed_data):
        content = json.loads(embed_data.content)
        user = self.client.get_user(embed_data.user_id)
        channel = self.client.get_channel(embed_data.channel_id)

        embed = Embed(
            title=content.get('title', None),
            description=content.get('description', None),
            color=content.get('color', None) or 0x4f545c,
        )
        for field in content.get('fields', []):
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False),
            )
        embed.set_footer(
            text=f'ID: {embed_data._id} | @{user.name}'
        )
        author = content.get('author', None)
        if author:
            embed.set_author(
                name=author.get('name', None),
                icon_url=author.get('icon_url', None),
            )

        # If embed already has a message id it was posted before -> try to edit
        if embed_data.message_id:
            message = await channel.fetch_message(embed_data.message_id)
            if not message:
                raise commands.CommandError('Cannot find message to edit')
            await message.edit(embed=embed)
        else:
            message = await channel.send(embed=embed)

        return message

    @commands.group(
        name='e',
        aliases=['embed'],
        invoke_without_command=True,
    )
    async def embed_base(self, ctx):
        pass

    @embed_base.command(
        name='add',
        aliases=['post'],
    )
    async def embed_add(self, ctx, channel: TextChannel = None, *, user_input=''):
        if not channel or (not user_input and len(ctx.message.attachments) == 0):
            await ctx.send("""Please provide a string, a link to a pastebin or a file
Template:
```
{
    "title": "Title1",
    "description": "description",
    "fields": [
        {
            "name": "Field1",
            "value": "Value1",
            "inline": true
        },
        {
            "name": "Field2",
            "value": "Value2",
            "inline": true
        }
    ],
    "author": {
        "name": "Author_Name",
        "icon_url": "https://www.google.com/favicon.ico"
    },
    "color": null
}
```"""
                           )
            return

        if len(ctx.message.attachments) == 1:
            attachment = ctx.message.attachments[0]
            async with self.client.session.get(attachment.url) as response:
                if not response.status == 200:
                    return
                user_input = await response.text()
        elif user_input.startswith('https://pastebin.com'):
            url = user_input.split()[0].replace('pastebin.com/', 'pastebin.com/raw/')
            async with self.client.session.get(url) as response:
                user_input = await response.text()

        try:
            content_dict = json.loads(user_input.replace('`', '').replace('\n', ''))
        except json.JSONDecodeError as e:
            await ctx.send(f'Error parsing json {e}')
            return

        embed_data = EmbedData(
            user_id=ctx.author.id,
            channel_id=channel.id,
            content=json.dumps(content_dict),
            date=datetime.now(tz=timezone.utc).isoformat(),
            message_id=0,
        )

        with self.client.state.get_session() as session:
            session.add(embed_data)

        # Save to db so it includes the _id (primary key)
        try:
            message = await self.post_embed(embed_data)
            embed_data.message_id = message.id
        except Exception as error:
            await ctx.send('Error during embed creation - check error log (+error)')
            await self.client.log_error(error, ctx)
            with self.client.state.get_session() as session:
                session.query(EmbedData).filter_by(_id=embed_data._id).delete()
            return
        # update entry with the correct message_id
        with self.client.state.get_session() as session:
            session.add(embed_data)

        await ctx.send(f'Embed added {message.jump_url}')

    @embed_base.command(
        name='print',
        aliases=['show']
    )
    async def embed_print(self, ctx, _id: int):
        with self.client.state.get_session() as session:
            embed_data = session.query(EmbedData).filter_by(_id=_id).first()

        if not embed_data:
            await ctx.send('Embed ID not found in Database')
            return

        to_send = json.dumps(json.loads(embed_data.content), indent=2)
        if len(to_send) > 1950:
            await ctx.send(file=File(
                fp=BytesIO(to_send.encode()),
                filename=f'Embed_{embed_data._id}.json'
            ))
        else:
            await ctx.send(f'```\n{to_send}```')

    @embed_base.command(
        name='edit',
    )
    async def embed_edit(self, ctx, embed_id: int, *, user_input=''):
        if len(ctx.message.attachments) == 1:
            attachment = ctx.message.attachments[0]
            async with self.client.session.get(attachment.url) as response:
                if not response.status == 200:
                    return
                user_input = await response.text()
        elif user_input.startswith('https://pastebin.com'):
            url = user_input.split()[0].replace('pastebin.com/', 'pastebin.com/raw/')
            async with self.client.session.get(url) as response:
                user_input = await response.text()

        try:
            content_dict = json.loads(user_input.replace('`', '').replace('\n', ''))
        except json.JSONDecodeError as e:
            await ctx.send(f'Error parsing json {e}')
            return

        with self.client.state.get_session() as session:
            embed_data = session.query(EmbedData).filter_by(_id=embed_id).first()
            embed_data.content = json.dumps(content_dict)
            try:
                message = await self.post_embed(embed_data)
                await ctx.send(f'Embed updated {message.jump_url}')
            except Exception as error:
                await ctx.send('Error during embed edit - check error log (+error)')
                await self.client.log_error(error, ctx)

    @embed_base.command(
        name='delete',
        aliases=['archive', 'del'],
    )
    async def embed_delete(self, ctx, embed_ids: commands.Greedy[int]):
        res = []
        for embed_id in embed_ids:
            with self.client.state.get_session() as session:
                db_query = session.query(EmbedData).filter_by(_id=embed_id)
                embed_data = db_query.first()
                if not embed_data:
                    res.append(f'{embed_id}: Embed ID not found in Database')
                    continue
                if not embed_data.message_id:
                    res.append(f'{embed_id}: Is already archived')
                    continue
                try:
                    channel = self.client.get_channel(embed_data.channel_id)
                    message = await channel.fetch_message(embed_data.message_id)
                    await message.delete()
                    res.append(f'{embed_id}: Embed archived')
                except NotFound:
                    res.append(f'{embed_id}: Embed was deleted manually - archiving db entry')
                    pass
                db_entry = session.query(EmbedData).filter_by(_id=embed_id).first()
                db_entry.message_id = 0

        await ctx.send('```\n' + '\n'.join(res) + '```')

    @embed_base.command(
        name='list',
        aliases=['active']
    )
    async def embed_list(self, ctx):
        with self.client.state.get_session() as session:
            embeds = session.query(EmbedData).filter(EmbedData.message_id != 0).all()
            to_print = ['Active Embeds:']

            if not embeds:
                await ctx.send('No active found')
                return

            await ctx.trigger_typing()

            for ed in embeds:
                try:
                    channel = self.client.get_channel(ed.channel_id)
                    message = await channel.fetch_message(ed.message_id)
                except NotFound:
                    ed.message_id = 0
                    to_print.append(f'{ed._id}: message not found in discord - db updated')
                    continue
                title = json.loads(ed.content).get('title', '')
                to_print.append(f'{ed._id}: {channel.mention} {title} ><{message.jump_url}>')

        for i in range(0, len(to_print), 11):
            await ctx.send('\n'.join(to_print[i:i+11]))

    @embed_base.command(
        name='search',
        aliases=['find'],
    )
    async def embed_search(self, ctx, *, search_term):
        search_term = search_term.replace('`', '')
        with self.client.state.get_session() as session:
            embeds = session.query(EmbedData).filter(
                EmbedData.content.like(f'%{search_term}%')).all()

            if not embeds:
                await ctx.send('No embeds found for this query')
                return

            await ctx.trigger_typing()

            to_print = ['Found these embeds:']

            for ed in embeds:
                title = json.loads(ed.content).get('title', '')
                to_print.append(
                    f'ID: {ed._id} | Title: {title} | Created: {ed.date}'
                    f'{" **Active **" if bool(ed.message_id) else " **Inactive **"}'
                )

        for i in range(0, len(to_print), 20):
            await ctx.send('\n'.join(to_print[i:i+11]))


def setup(client):
    client.add_cog(EmbedController(client))
