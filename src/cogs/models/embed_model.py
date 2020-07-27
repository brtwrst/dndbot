# pylint: disable=E0402, E0211, E1101
import json
from discord import Embed as DiscordEmbed
from .core import ModelError, BaseDB, BaseModel, EmbedData


class EmbedDB(BaseDB):
    def __init__(self, client):
        super().__init__(client, model_class=Embed)

    def create_new(self, content, date, user_id=None, channel_id=None, message_id=None):
        data = EmbedData(
            content=content,
            date=date,
            user_id=user_id,
            channel_id=channel_id,
            message_id=message_id,
        )

        with self.client.state.get_session() as session:
            session.add(data)

        return self.model_class(self.client, data)


class Embed(BaseModel):
    table_type = EmbedData

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def user_id(self):
        return self.data.user_id

    @user_id.setter
    def user_id(self, value):
        self.data.user_id = value
        self.save_to_db()

    @property
    def channel_id(self):
        return self.data.channel_id

    @channel_id.setter
    def channel_id(self, value):
        self.data.channel_id = value
        self.save_to_db()

    @property
    def message_id(self):
        return self.data.message_id

    @message_id.setter
    def message_id(self, value):
        self.data.message_id = value
        self.save_to_db()

    @property
    def content(self):
        return self.data.content

    @content.setter
    def content(self, value):
        self.data.content = value
        self.save_to_db()

    @property
    def date(self):
        return self.data.date

    @date.setter
    def date(self, value):
        self.data.date = value
        self.save_to_db()

    async def get_discord_message(self):
        if not self.message_id or not self.channel_id:
            return None
        try:
            channel = self.client.get_channel(self.channel_id)
            message = await channel.fetch_message(self.message_id)
            return message
        except Exception:
            self.message_id = None
            return None

    async def post(self, channel_id=None):
        if channel_id:
            self.channel_id = channel_id

        if not self.channel_id:
            raise ModelError('Error posting Embed - no channel assigned yet')

        if self.message_id:
            await self.remove()

        channel = self.client.get_channel(self.channel_id)
        if not channel:
            raise ModelError('Error posting Embed - channel does not exist')

        embed = self.construct_discord_embed()

        message = await channel.send(embed=embed)
        self.message_id = message.id

        return message

    async def remove(self):
        status = 'Message not found'
        message = await self.get_discord_message()
        if message:
            await message.delete()
            status = 'Message deleted'
        self.message_id = None

        return status * bool(message)

    async def delete(self):
        await self.remove()
        with self.client.state.get_session() as session:
            status = session.query(type(self).table_type).filter_by(_id=self._id).delete()
        return status

    async def update(self):
        message = await self.get_discord_message()
        if not message:
            raise ModelError('Error updating Message - Message containing embed not found.')

        await message.edit(embed=self.construct_discord_embed())
        return message

    def construct_discord_embed(self):
        content = json.loads(self.content)

        if 'embed' in content:
            content = content['embed']
        elif 'embeds' in content:
            content = content['embeds'][0]

        user = self.client.get_user(self.user_id) if self.user_id else None

        embed = DiscordEmbed(
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
            text=f'ID: {self._id}' + (f' | @{user.name}' if user else "")
        )

        author = content.get('author', None)
        if author:
            embed.set_author(
                name=author.get('name', None),
                url=author.get('url', DiscordEmbed.Empty),
                icon_url=author.get('icon_url', DiscordEmbed.Empty),
            )

        return embed
