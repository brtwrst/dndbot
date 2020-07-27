"""This is a cog for a discord.py bot.
It will add commands to manage embeds.
"""
# pylint: disable=E0402, E0211
import json
from io import BytesIO
from datetime import datetime, timezone
from discord.ext import commands
from discord.errors import NotFound
from discord import Embed, TextChannel, File, Role
from sqlalchemy.orm.exc import NoResultFound
from .models.db_core import EmbedData, QuestData


class EmbedController(commands.Cog, name='EmbedController'):
    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    def construct_embed(self, embed_data):
        content = json.loads(embed_data.content)

        if 'embed' in content:
            content = content['embed']
        elif 'embeds' in content:
            content = content['embeds'][0]

        user = self.client.get_user(embed_data.user_id) if embed_data.user_id else None

        embed = Embed(
            title=content.get('title', None),
            description=content.get('description', None),
            url=content.get('url', None),
            color=content.get('color', None) or 0x4f545c,
        )
        for field in content.get('fields', []):
            embed.add_field(
                name=field['name'],
                value=field['value'],
                inline=field.get('inline', False),
            )
        embed.set_footer(
            text=f'ID: {embed_data._id}' + (f' | @{user.name}' if user else "")
        )
        author = content.get('author', None)
        if author:
            embed.set_author(
                name=author.get('name', None),
                url=author.get('url', Embed.Empty),
                icon_url=author.get('icon_url', Embed.Empty),
            )

        return embed

    def add_embed_to_db(self, embed_data):
        with self.client.state.get_session() as session:
            session.add(embed_data)
        return embed_data._id

    async def post_embed(self, embed_id, new_channel_id=None):
        with self.client.state.get_session() as session:
            embed_data = session.query(EmbedData).filter_by(_id=embed_id).one()

        if embed_data.message_id:
            await self.delete_embed_message(embed_id)

        if new_channel_id:
            with self.client.state.get_session() as session:
                embed_data = session.query(EmbedData).filter_by(_id=embed_id).one()
                embed_data.channel_id = new_channel_id

        channel = self.client.get_channel(embed_data.channel_id)
        if not channel:
            raise ValueError('Error posting Embed - channel does not exist')

        embed = self.construct_embed(embed_data)
        message = await channel.send(embed=embed)

        with self.client.state.get_session() as session:
            embed_data = session.query(EmbedData).filter_by(_id=embed_id).one()
            embed_data.message_id = message.id

        return message

    async def update_embed(self, embed_id):
        await self.edit_embed(embed_id, new_content=None)

    async def edit_embed(self, embed_id, new_content):
        with self.client.state.get_session() as session:
            embed_data = session.query(EmbedData).filter_by(_id=embed_id).one()
            if new_content:
                embed_data.content = json.dumps(new_content)
        try:
            channel = self.client.get_channel(embed_data.channel_id)
            if not channel:
                raise ValueError('Error editing Embed - channel does not exist')
            try:
                message = await channel.fetch_message(embed_data.message_id)
                if not message:
                    raise NotFound
                else:
                    embed = self.construct_embed(embed_data)
                    await message.edit(embed=embed)
                    status = 'Embed updated'
            except NotFound:
                message = await self.post_embed(embed_id, embed_data.channel_id)
                status = 'Embed not found - reposted'
            return f'{status} {message.jump_url}'
        except Exception as error:
            await self.client.log_error(error, None)
            return 'Error during embed edit - check error log (+error)'

    async def delete_embed_message(self, embed_id):
        with self.client.state.get_session() as session:
            try:
                embed_data = session.query(EmbedData).filter_by(_id=embed_id).one()
                channel = self.client.get_channel(embed_data.channel_id)
                message = await channel.fetch_message(embed_data.message_id)
                embed_data.message_id = 0
                await message.delete()
            except NotFound:
                return 'Embed message not found in discord'
            except NoResultFound:
                return 'Embed not found in database'

        return 'Embed message Deleted'

    async def get_content(self, ctx):
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

        try:
            content_dict = json.loads(user_input.replace('`', ''))
        except json.JSONDecodeError as e:
            await ctx.send(f'Error parsing json {e}')
            return

        return content_dict

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
    async def embed_add(self, ctx, channel: TextChannel = None, *, user_input=''):
        """Add an embed to a channel using a JSON Object"""
        if not channel or (not user_input and len(ctx.message.attachments) == 0):
            await ctx.send('Please provide a string, a link to a pastebin or a file')
            return

        content_dict = await self.get_content(ctx)

        embed_data = EmbedData(
            user_id=ctx.author.id,
            channel_id=channel.id,
            content=json.dumps(content_dict),
            date=datetime.now(tz=timezone.utc).isoformat(),
            message_id=0,
        )

        embed_id = self.add_embed_to_db(embed_data)

        await ctx.send(f'Embed added')
        await ctx.invoke(self.client.get_command('embed post'), embed_id)


    @embed_base.command(
        name='post',
        aliases=['repost']
    )
    async def embed_post(self, ctx, embed_id, channel: TextChannel = None):
        message = await self.post_embed(embed_id, channel.id if channel else None)
        await ctx.send(f'Embed posted {message.jump_url}')

    @embed_base.command(
        name='edit',
    )
    async def embed_edit(self, ctx, embed_id: int, *, user_input=''):
        """Edit an embed using a JSON Object"""
        content_dict = await self.get_content(ctx)

        res = await self.edit_embed(embed_id, content_dict)
        await ctx.send(res)

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
        if len(to_send) > 1000:
            await ctx.send(file=File(
                fp=BytesIO(to_send.encode()),
                filename=f'Embed_{embed_data._id}.json'
            ))
        else:
            await ctx.send(f'```\n{to_send}```')

    @embed_base.command(
        name='delete',
        aliases=['archive', 'del'],
    )
    async def embed_delete(self, ctx, embed_ids: commands.Greedy[int]):
        statuses = []
        for embed_id in embed_ids:
            status = await self.delete_embed_message(embed_id)
            statuses.append(f'{embed_id}: ' + status)
        await ctx.send('```\n' + '\n'.join(statuses) + '```')

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

class QuestController(commands.Cog, name='QuestController'):
    def __init__(self, client, embed_controller):
        self.client = client
        self.ec = embed_controller
        self.statuses = {
            0: 'Offen',
            1: 'In Progress',
            2: 'Erfolgreich (Warte auf Bericht)',
            3: 'Erfolglos (Warte auf Bericht)',
            4: 'Abgeschlossen',
        }

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    def create_embed_content(self, quest_data):
        content_dict = {
            'title': quest_data.title,
            'fields': [
              {
                'name': 'Quest Nummer',
                'value': f'{quest_data._id}',
                'inline': True
              },
              {
                'name': 'Datum',
                'value': f'{quest_data.date}',
                'inline': True
              },
              {
                'name': 'Multi Session',
                'value': f'{quest_data.multi}',
                'inline': True
              },
              {
                'name': 'Tier',
                'value': f'T{quest_data.tier}',
                'inline': True
              },
              {
                'name': 'Rang',
                'value': f'{self.client.mainguild.get_role(quest_data.rank).mention}',
                'inline': True
              },
              {
                'name': 'Belohnung',
                'value': f'{quest_data.reward}',
                'inline': True
              },
              {
                'name': 'Beschreibung',
                'value': f'{quest_data.description}',
                'inline': False
              }
            ],
            'author': {
              'name': f'Status: {self.statuses[quest_data.status]}',
            }
        }

        return content_dict

    @commands.group(
        name='quest',
        aliases=['q'],
        invoke_without_command=True,
    )
    async def quest_base(self, ctx):
        pass

    @quest_base.command(
        name='add',
    )
    async def quest_add(
        self, ctx,
        _id: int,
        date: str,
        multi: str,
        tier: int,
        rank: Role,
        reward: str,
        title: str,
        *,
        description: str,
    ):
        quest_data = QuestData(
            _id=_id,
            embed_id = None,
            date = date,
            multi = multi,
            tier = tier,
            rank = rank.id,
            reward = reward,
            title = title,
            description = description,
            status = 0,
        )

        embed_data = EmbedData(
            user_id=0,
            channel_id=0,
            content=json.dumps(self.create_embed_content(quest_data)),
            date=datetime.now(tz=timezone.utc).isoformat(),
            message_id=0,
            )

        embed_id = self.ec.add_embed_to_db(embed_data)

        with self.client.state.get_session() as session:
            session.add(quest_data)
            quest_data.embed_id = embed_id

        await ctx.send(f'Quest added - Embed ID: {embed_id}')

    @quest_base.command(
        name='edit',
    )
    async def quest_edit(
        self, ctx,
        _id: int,
        date: str,
        multi: str,
        tier: int,
        rank: Role,
        reward: str,
        title: str,
        *,
        description: str,
    ):
        with self.client.state.get_session() as session:
            quest_data = session.query(QuestData).filter_by(_id=_id).one()

            quest_data.date = date
            quest_data.multi = multi
            quest_data.tier = tier
            quest_data.rank = rank.id
            quest_data.reward = reward
            quest_data.title = title
            quest_data.description = description

            status = await self.ec.edit_embed(quest_data.embed_id, self.create_embed_content(quest_data))
            await ctx.send('Quest edited | ' + str(status))


    @quest_base.command(
        name='show',
    )
    async def quest_show(self, ctx, quest_id):
        with self.client.state.get_session() as session:
            quest_data = session.query(QuestData).filter_by(_id=quest_id).one()

        to_print = ['+quest edit']
        to_print.append(f'"{quest_data._id}"')
        to_print.append(f'"{quest_data.date}"')
        to_print.append(f'"{quest_data.multi}"')
        to_print.append(f'"{quest_data.tier}"')
        to_print.append(f'"{quest_data.rank}"')
        to_print.append(f'"{quest_data.reward}"')
        to_print.append(f'"{quest_data.title}"')
        to_print.append(f'{quest_data.description}')

        await ctx.send('```\n' + ' '.join(to_print) + '```')



def setup(client):
    ec = EmbedController(client)
    client.add_cog(ec)
    client.add_cog(QuestController(client, ec))
