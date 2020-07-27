"""This is a cog for a discord.py bot.
It will add commands to manage embeds.
"""
# pylint: disable=E0402, E0211
import json
from io import BytesIO
from datetime import datetime, timezone
from discord.ext import commands
from discord import TextChannel, File
from .models.core import DBError, ModelError
from .models.embed_model import EmbedDB


class EmbedController(commands.Cog, name='EmbedController'):
    def __init__(self, client):
        self.client = client
        self.EmbedDB = EmbedDB(client)

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    async def validate_content(self, ctx):
        user_input = ctx.kwargs.get('user_input', None)
        if not user_input:
            return None

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

        # Make sure it's valid Json
        content_dict = json.loads(user_input.replace('`', ''))

        return json.dumps(content_dict)

    @commands.group(
        name='embed',
        aliases=['e'],
        invoke_without_command=True,
    )
    async def embed_base(self, ctx):
        pass

    @embed_base.command(
        name='add',
    )
    async def embed_add(self, ctx, channel: commands.Greedy[TextChannel] = None, *, user_input=''):
        """Add an embed using a JSON Object"""
        if not user_input and len(ctx.message.attachments) == 0:
            await ctx.send('Please provide a string, a link to a pastebin or a file')
            return

        content = await self.validate_content(ctx)

        if channel:
            channel = channel[0]

        try:
            new_embed = self.EmbedDB.create_new(
                user_id=ctx.author.id,
                channel_id=channel.id if channel else None,
                content=content,
                date=datetime.now(tz=timezone.utc).isoformat(),
                message_id=0,
            )
        except DBError as e:
            await ctx.send(e)
            return

        await ctx.send(f'Embed added. ID: {new_embed._id}')
        if channel:
            try:
                message = await new_embed.post()
                await ctx.send(message.jump_url)
            except (ModelError, DBError) as e:
                await ctx.send(e)

    @embed_base.command(
        name='post',
        aliases=['repost']
    )
    async def embed_post(self, ctx, embed_id, channel: TextChannel = None):
        """Post or repost an embed"""
        try:
            embed = self.EmbedDB.query_one(_id=embed_id)
            message = await embed.post(channel.id if channel else None)
            await ctx.send('Embed Posted ' + message.jump_url)
        except (ModelError, DBError) as e:
            await ctx.send(e)

    @embed_base.command(
        name='edit',
    )
    async def embed_edit(self, ctx, embed_id: int, *, user_input=''):
        """Edit an embed using a JSON Object"""
        try:
            content = await self.validate_content(ctx)

            embed = self.EmbedDB.query_one(_id=embed_id)
            embed.content = content
            await ctx.send('Embed update successful - trying to update message')
            message = await embed.update()
            await ctx.send('Message update successful ' + message.jump_url)
        except (json.JSONDecodeError, DBError, ModelError) as e:
            await ctx.send(e)

    @embed_base.command(
        name='show_content',
        aliases=['print_content']
    )
    async def embed_print(self, ctx, _id: int):
        """Print the embeds content JSON Object"""
        try:
            embed = self.EmbedDB.query_one(_id=_id)

            if not embed:
                await ctx.send('Embed ID not found in Database')
                return

            to_send = json.dumps(json.loads(embed.content), indent=2)
            if len(to_send) > 1000:
                await ctx.send(file=File(
                    fp=BytesIO(to_send.encode()),
                    filename=f'Embed_{embed._id}.json'
                ))
            else:
                await ctx.send(f'```\n{to_send}```')
        except (ModelError, DBError) as e:
            await ctx.send(e)

    @embed_base.command(
        name='delete',
        aliases=['archive', 'del', 'remove'],
    )
    async def embed_delete(self, ctx, embed_ids: commands.Greedy[int]):
        statuses = []
        for embed_id in embed_ids:
            embed = self.EmbedDB.query_one(_id=embed_id)
            if embed:
                status = await embed.remove()
                statuses.append(f'{embed_id}: ' + status)
        await ctx.send('```\n' + '\n'.join(statuses) + '```')

    @embed_base.command(
        name='list',
        aliases=['active']
    )
    async def embed_list(self, ctx):
        embeds = self.EmbedDB.query_all_filter(self.EmbedDB.table_class.message_id != 0)
        to_print = ['Active Embeds:']

        if not embeds:
            await ctx.send('No active embeds found')
            return

        await ctx.trigger_typing()

        for embed in embeds:
            message = await embed.get_discord_message()
            if not message:
                to_print.append(f'{embed._id}: message not found in discord - db updated')
                continue
            channel = message.channel
            title = json.loads(embed.content).get('title', '')
            to_print.append(f'{embed._id}: {channel.mention} {title} <{message.jump_url}>')

        for i in range(0, len(to_print), 11):
            await ctx.send('\n'.join(to_print[i:i+11]))

    # @embed_base.command(
    #     name='search',
    #     aliases=['find'],
    # )
    # async def embed_search(self, ctx, *, search_term):
    #     search_term = search_term.replace('`', '')
    #     with self.client.state.get_session() as session:
    #         embeds = session.query(EmbedData).filter(
    #             EmbedData.content.like(f'%{search_term}%')).all()

    #         if not embeds:
    #             await ctx.send('No embeds found for this query')
    #             return

    #         await ctx.trigger_typing()

    #         to_print = ['Found these embeds:']

    #         for ed in embeds:
    #             title = json.loads(ed.content).get('title', '')
    #             to_print.append(
    #                 f'ID: {ed._id} | Title: {title} | Created: {ed.date}'
    #                 f'{" **Active **" if bool(ed.message_id) else " **Inactive **"}'
    #             )

    #     for i in range(0, len(to_print), 20):
    #         await ctx.send('\n'.join(to_print[i:i+11]))


def setup(client):
    client.add_cog(EmbedController(client))
