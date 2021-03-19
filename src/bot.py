"""DND5e Discord Bot

"""
import json
from datetime import datetime, timezone
from os import path, listdir
from aiohttp import ClientSession
from discord import Activity, Message, Intents, AllowedMentions
from discord.ext.commands import Bot, Context
from cogs.models.core import DBConnector


class DNDBot(Bot):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.session = None
        with open('../state/config.json') as conffile:
            self.config = json.load(conffile)
        self.last_errors = []
        self.default_activity = Activity(name='other Characters (+help)', type=0)
        self.error_activity = Activity(name='! other Characters (+help)', type=0)
        self.error_string = 'Sorry, something went wrong. We will look into it.'
        self.mainguild = None
        self.state = DBConnector(db_path='sqlite:///../state/state.db.sqlite3')

    async def start(self, *args, **kwargs):
        self.session = ClientSession()
        await super().start(self.config["bot_key"], *args, **kwargs)

    async def close(self):
        await self.session.close()
        await super().close()

    async def log_error(self, error, error_source=None):
        self.last_errors.append((
            error,
            datetime.now(tz=timezone.utc),
            error_source,
            error_source.message.content if isinstance(error_source, Context) else None
        ))
        await client.change_presence(activity=self.error_activity)

    def user_is_admin(self, user):
        if user.id in self.config['admins']:
            return True
        try:
            user_roles = [role.id for role in user.roles]
        except AttributeError:
            return False
        permitted_roles = self.config['admin_roles']
        return any(role in permitted_roles for role in user_roles)


intents = Intents.default()
intents.members = True

client = DNDBot(
    command_prefix=('+'),
    description='Hi I am DNDBot!',
    max_messages=15000,
    intents=intents,
    allowed_mentions=AllowedMentions(everyone=False, users=True, roles=True)
)

STARTUP_EXTENSIONS = []
for file in listdir(path.join(path.dirname(__file__), 'cogs/')):
    filename, ext = path.splitext(file)
    if '.py' in ext:
        STARTUP_EXTENSIONS.append(f'cogs.{filename}')

for extension in reversed(STARTUP_EXTENSIONS):
    try:
        client.load_extension(f'{extension}')
    except Exception as e:
        client.last_errors.append((e, datetime.utcnow(), None, None))
        exc = f'{type(e).__name__}: {e}'
        print(f'Failed to load extension {extension}\n{exc}')


@client.event
async def on_ready():
    print('\nActive in these guilds/servers:')
    [print(g.name) for g in client.guilds]
    print('DNDBot started successfully')
    client.mainguild = client.get_guild(client.config['mainguild'])
    return True


client.run()
print('DNDBot has exited')
