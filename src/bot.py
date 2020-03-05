"""DiceBot Discord Bot

"""
import json
from datetime import datetime
from os import path, listdir
from discord.ext.commands import Bot
from discord import DMChannel
from cogs.utils.diceengine import DiceEngine
# from aiohttp import ClientSession


class DiceBot(Bot):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.session = None
        with open('../config.json') as conffile:
            self.config = json.load(conffile)
        self.last_errors = []
        self.dice_engine = DiceEngine()

    async def start(self, *args, **kwargs):
        # self.session = ClientSession()
        await super().start(self.config["bot_key"], *args, **kwargs)

    async def close(self):
        # await self.session.close()
        await super().close()

    def user_is_admin(self, user):
        try:
            user_roles = [role.id for role in user.roles]
        except AttributeError:
            return False
        permitted_roles = self.config['admin_roles']
        return any(role in permitted_roles for role in user_roles)


client = DiceBot(
    command_prefix=('!'),
    description='Hi I am DiceBot!',
    max_messages=15000
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
        client.last_errors.append((e, datetime.utcnow(), None))
        exc = f'{type(e).__name__}: {e}'
        print(f'Failed to load extension {extension}\n{exc}')


@client.event
async def on_ready():
    print('\nActive in these guilds/servers:')
    [print(g.name) for g in client.guilds]
    print('DiceBot started successfully')
    return True


@client.event
async def on_message(msg):
    if isinstance(msg.channel, DMChannel):
        return
    await client.process_commands(msg)


client.run()
print('DiceBot has exited')
