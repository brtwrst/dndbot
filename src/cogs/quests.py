"""This is a cog for a discord.py bot.
It will add commands to manage quests.
"""
# pylint: disable=E0402, E0211
from datetime import datetime, timezone
from discord.ext import commands
from discord import Role, TextChannel
from .models.core import DBError, ModelError
from .models.quest_model import QuestDB
from .models.embed_model import EmbedDB


class QuestController(commands.Cog, name='QuestController'):
    def __init__(self, client):
        self.client = client
        self.QuestDB = QuestDB(client)
        self.EmbedDB = EmbedDB(client)

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    @commands.group(
        name='quest',
        aliases=['q'],
        invoke_without_command=True,
    )
    async def quest_base(self, ctx):
        """Add/Change Quests"""
        pass

    @quest_base.command(
        name='add',
    )
    async def quest_add(
        self, ctx,
        quest_id: int,
        date: str,
        multi: str,
        tier: int,
        rank: Role,
        reward: str,
        title: str,
        *,
        description: str,
    ):
        """Add a quest"""
        try:
            quest = self.QuestDB.create_new(
                quest_id=quest_id,
                date=date,
                multi=multi,
                tier=tier,
                rank_id=rank.id,
                reward=reward,
                title=title,
                description=description,
            )

            embed = self.EmbedDB.create_new(
                user_id=None,
                channel_id=None,
                content=quest.create_embed_content(),
                date=datetime.now(tz=timezone.utc).isoformat(),
                message_id=None,
            )

            quest.embed_id = embed.id
        except (DBError, ModelError) as e:
            await ctx.send(e)

        await ctx.send(f'Quest {quest.id} added - Embed ID: {embed.id}')

    @quest_base.command(
        name='post',
    )
    async def quest_post(self, ctx, quest_id: int, channel: TextChannel = None):
        """Post a quest embed to a channel"""
        try:
            quest = self.QuestDB.query_one(id=quest_id)
            embed = self.EmbedDB.query_one(id=quest.embed_id)
            message = await embed.post(channel.id if channel else None)
            await ctx.send('Quest Posted ' + message.jump_url)
        except (ModelError, DBError) as e:
            await ctx.send(e)

    @quest_base.command(
        name='edit',
        aliases=['update']
    )
    async def quest_edit(self, ctx, quest_id: int, attribute: str, *, value: str):
        """Edit a quest"""
        value = value.replace('`', '')
        quest = self.QuestDB.query_one(id=quest_id)
        await quest.edit(attribute, value)
        await ctx.send('Quest updated')

    @quest_base.command(
        name='show',
    )
    async def quest_show(self, ctx, quest_id):
        """Show the attributes of a quest"""
        quest = self.QuestDB.query_one(id=quest_id)

        to_print = []
        to_print.append(f'**date:** `{quest.date}`')
        to_print.append(f'**multi:** `{quest.multi}`')
        to_print.append(f'**tier:** `{quest.tier}`')
        to_print.append(f'**rank_id:** `{quest.rank_id}`')
        to_print.append(f'**reward:** `{quest.reward}`')
        to_print.append(f'**title:** `{quest.title}`')
        to_print.append(f'**description:** `{quest.description}`')

        await ctx.send('\n'.join(to_print))

    @quest_base.command(
        name='list',
    )
    async def quest_list(self, ctx):
        """List all quests"""
        quests = self.QuestDB.query_all()

        await ctx.send('```\n' + ', '.join(str(q.id) for q in quests) + '```')

    @quest_base.command(
        name='delete',
    )
    async def quest_delete(self, ctx, quest_id):
        """Delete a quest"""
        quest = self.QuestDB.query_one(id=quest_id)
        if quest:
            if await quest.delete() == 1:
                await ctx.send(f'Quest {quest_id} deleted')
            else:
                raise commands.CommandError('Unexpected number of deleted rows')


def setup(client):
    client.add_cog(QuestController(client))
