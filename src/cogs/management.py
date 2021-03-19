"""This is a cog for a discord.py bot.
It will add some management commands to a bot.

Commands:
    load            load an extension / cog
    unload          unload an extension / cog
    reload          reload an extension / cog
    cogs            show currently active extensions / cogs
    error           print the traceback of the last unhandled error to chat
"""
import json
import traceback
import typing
import subprocess
import re
from datetime import datetime
from os import path, listdir
from discord import Embed, DMChannel
from discord.ext import commands


class Management(commands.Cog, name='Management'):
    def __init__(self, client):
        self.client = client
        self.reload_config()

    async def cog_check(self, ctx):
        return self.client.user_is_admin(ctx.author)

    @commands.Cog.listener()
    async def on_ready(self):
        loaded = self.client.extensions
        unloaded = [x for x in self.crawl_cogs() if x not in loaded and 'extra.' not in x]
        activity = self.client.error_activity if unloaded else self.client.default_activity
        await self.client.change_presence(activity=activity)

    def reload_config(self):
        with open("../state/config.json") as conffile:
            self.client.config = json.load(conffile)

    def crawl_cogs(self, directory='cogs'):
        cogs = []
        for element in listdir(directory):
            if element in ('samples', 'utils', 'models'):
                continue
            abs_el = path.join(directory, element)
            if path.isdir(abs_el):
                cogs += self.crawl_cogs(abs_el)
            else:
                filename, ext = path.splitext(element)
                if ext == '.py':
                    dot_dir = directory.replace('\\', '.')
                    dot_dir = dot_dir.replace('/', '.')
                    cogs.append(f'{dot_dir}.' + filename)
        return cogs

    # ----------------------------------------------
    # Function to load extensions
    # ----------------------------------------------
    @commands.command(
        name='load',
        brief='Load bot extension',
        description='Load bot extension\n\nExample: !load cogs.stats',
    )
    async def load_extension(self, ctx, extension_name):
        for cog_name in self.crawl_cogs():
            if extension_name in cog_name:
                target_extension = cog_name
                break
        try:
            self.client.load_extension(target_extension)
        except Exception as e:
            await self.client.log_error(e, None)
            await ctx.send(f'```py\n{type(e).__name__}: {str(e)}\n```')
            return
        await ctx.send(f'```css\nExtension [{target_extension}] loaded.```')

    # ----------------------------------------------
    # Function to unload extensions
    # ----------------------------------------------
    @commands.command(
        name='unload',
        brief='Unload bot extension',
        description='Unload bot extension\n\nExample: !unload cogs.stats',
    )
    async def unload_extension(self, ctx, extension_name):
        for cog_name in self.client.extensions:
            if extension_name in cog_name:
                target_extension = cog_name
                break
        if target_extension.lower() in 'cogs.management':
            await ctx.send(
                f"```diff\n- {target_extension} can't be unloaded" +
                f"\n+ try !reload {target_extension}!```"
            )
            return
        if self.client.extensions.get(target_extension) is None:
            return
        self.client.unload_extension(target_extension)
        await ctx.send(f'```css\nExtension [{target_extension}] unloaded.```')

    # ----------------------------------------------
    # Function to reload extensions
    # ----------------------------------------------
    @commands.command(
        name='reload',
        brief='Reload bot extension',
        description='Reload bot extension\n\nExample: !reload cogs.stats',
        aliases=['re']
    )
    async def reload_extension(self, ctx, extension_name):
        target_extensions = []
        if extension_name == 'all':
            target_extensions = [__name__] + \
                [x for x in self.client.extensions if not x == __name__]
        else:
            for cog_name in self.client.extensions:
                if extension_name in cog_name:
                    target_extensions = [cog_name]
                    break
        if not target_extensions:
            return
        result = []
        for ext in target_extensions:
            try:
                self.client.reload_extension(ext)
                result.append(f'Extension [{ext}] reloaded.')
            except Exception as e:
                await self.client.log_error(e, None)
                result.append(f'#ERROR loading [{ext}]')
                continue
        result = '\n'.join(result)
        await ctx.send(f'```css\n{result}```')

    # ----------------------------------------------
    # Function to get bot extensions
    # ----------------------------------------------
    @commands.command(
        name='cogs',
        brief='Get loaded cogs',
        description='Get loaded cogs',
        aliases=['extensions'],
    )
    async def print_cogs(self, ctx):
        loaded = self.client.extensions
        unloaded = [x for x in self.crawl_cogs() if x not in loaded]
        response = ['\n[Loaded extensions]'] + ['\n  ' + x for x in loaded]
        response += ['\n[Unloaded extensions]'] + \
            ['\n  ' + x for x in unloaded]
        await ctx.send(f'```css{"".join(response)}```')
        return True

    # ----------------------------------------------
    # Function to stop the bot
    # ----------------------------------------------
    @commands.command(
        name='stop',
        aliases=['restart'],
    )
    async def stop_bot(self, ctx):
        """Stop and restart the bot"""
        await self.client.close()

    # ----------------------------------------------
    # Command to pull the latest changes from github
    # ----------------------------------------------
    @commands.command(
        name='gitpull',
    )
    async def git_pull(self, ctx):
        """Pull the latest changes from github"""
        await ctx.trigger_typing()
        try:
            output = subprocess.check_output(
                ['git', 'pull']).decode()
            await ctx.send('```git\n' + output + '\n```')
        except Exception as e:
            return await ctx.send(str(e))
        cog_re = re.compile(r'\s*src\/cogs\/(.+)\.py\s*\|\s*\d+\s*[+-]+')
        _cogs = [f'cogs.{i}' for i in cog_re.findall(output)]
        active_cogs = [i for i in _cogs if i in self.client.extensions]
        if active_cogs:
            for cog_name in active_cogs:
                await ctx.invoke(self.client.get_command('reload'), cog_name)


def setup(client):
    client.add_cog(Management(client))
