"""This is a cog for a discord.py bot.
It will add error handling and inspecting commands

Commands:
    error               List unhandled errors
      - traceback       print traceback of stored error

"""
# pylint: disable=E0402
import traceback
import typing
from datetime import datetime, timezone
from asyncio import TimeoutError as AsyncTimeoutError
from discord import Embed, DMChannel, errors as discord_errors
from discord.ext import commands


class ErrorHandler(commands.Cog, name='ErrorHandler'):
    def __init__(self, client):
        self.client = client

    # ----------------------------------------------
    # Error handler
    # ----------------------------------------------
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if not isinstance(ctx.channel, DMChannel):
            perms = ctx.channel.permissions_for(ctx.guild.get_member(self.client.user.id))
            try:
                if not perms.send_messages:
                    await ctx.author.send("I don't have permission to write in this channel.")
                    await self.try_delete(ctx)
                    return
            except discord_errors.Forbidden:
                return

            if not perms.embed_links:
                await ctx.author.send("I don't have permission to post embeds in this channel.")
                await self.try_delete(ctx)
                return

            if not perms.manage_messages:
                await ctx.author.send("I don't have permission to manage messages in this channel.")
                return

        usr = ctx.author.mention

        if isinstance(error, commands.CommandNotFound):
            await ctx.author.send(
                f'Unknown command ```\n{ctx.message.content.replace("```", "´´´")}\n```'
            )
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.author.send(error)
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            par = str(error.param)
            missing = par.split(": ")[0]
            if ':' in par:
                missing_type = ' (' + str(par).split(": ")[1] + ')'
            else:
                missing_type = ''
            await ctx.author.send(
                f'Missing parameter: `{missing}{missing_type}`'
            )
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.CheckFailure):
            await ctx.author.send(f'Sorry, you are not allowed to run this command.')
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.BadArgument):
            # It's in an embed to prevent mentions from working
            embed = Embed(
                title='Error',
                description=str(error),
                color=0x2ECC71
            )
            await ctx.author.send(embed=embed)
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.UnexpectedQuoteError):
            await ctx.author.send(f'Unexpected quote encountered ```\n{ctx.message.content}```')
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.InvalidEndOfQuotedStringError):
            await ctx.author.send(f'Invalid character after quote ```\n{ctx.message.content}```')
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.ExpectedClosingQuoteError):
            await ctx.author.send(f'Expected Closing Quote ```\n{ctx.message.content}```')
            await self.try_delete(ctx)
            return

        if isinstance(error, commands.CommandInvokeError):
            if isinstance(error.original, AsyncTimeoutError):
                await ctx.send(f'{usr} API Timeout - Please try again later')
                await self.client.log_error(error, ctx)
                return

        # In case of an unhandled error -> Save the error so it can be accessed later
        await ctx.send(f'{self.client.error_string}')
        await self.client.log_error(error, ctx)

        print(f'ERROR handler fallthrough:  {ctx.command}:', flush=True)
        traceback.print_exception(
            type(error), error, error.__traceback__
        )
        print('-------------------------------------------------------------', flush=True)

    async def try_delete(self, ctx):
        if isinstance(ctx.channel, DMChannel):
            return
        try:
            await ctx.message.delete()
        except discord_errors.Forbidden:
            pass

    # ----------------------------------------------
    # Error command Group
    # ----------------------------------------------
    @commands.group(
        invoke_without_command=True,
        name='error',
        hidden=True,
        aliases=['errors']
    )
    async def error(self, ctx, n: typing.Optional[int] = None):
        """Show a concise list of stored errors"""

        if n is not None:
            await self.print_traceback(ctx, n)
            return

        NUM_ERRORS_PER_PAGE = 5

        error_log = self.client.last_errors

        if not error_log:
            await ctx.send('Error log is empty')
            return

        response = [f'```css\nNumber of stored errors: {len(error_log)}']
        for i, exc_tuple in enumerate(error_log):
            exc, date, error_source, *_ = exc_tuple
            call_info = f'{"CMD:" + error_source.invoked_with if isinstance(error_source, commands.Context) else error_source}'
            response.append(
                f'{i}: ['
                + date.isoformat().split('.')[0]
                + '] - ['
                + call_info
                + f']\nException: {exc}'
            )
            if i % NUM_ERRORS_PER_PAGE == NUM_ERRORS_PER_PAGE-1:
                response.append('```')
                await ctx.send('\n'.join(response))
                response = [f'```css']
        if len(response) > 1:
            response.append('```')
            await ctx.send('\n'.join(response))

    @error.command(
        name='clear',
        aliases=['delete'],
    )
    async def error_clear(self, ctx, n: int = None):
        """Clear error with index [n]"""
        if n is None:
            self.client.last_errors = []
            await ctx.send('Error log cleared')
        else:
            self.client.last_errors.pop(n)
            await ctx.send(f'Deleted error #{n}')
        await self.client.change_presence(
            activity=self.client.default_activity
        )

    @error.command(
        name='traceback',
        aliases=['tb'],
    )
    async def error_traceback(self, ctx, n: int = None):
        """Print the traceback of error [n] from the error log"""
        await self.print_traceback(ctx, n)

    async def print_traceback(self, ctx, n):
        error_log = self.client.last_errors

        if not error_log:
            await ctx.send('Error log is empty')
            return

        if n is None:
            await ctx.send('Please specify an error index')
            await self.client.get_command('error').invoke(ctx)
            return

        if n >= len(error_log) or n < 0:
            await ctx.send('Error index does not exist')
            return

        exc, date, error_source, orig_content = error_log[n]
        delta = (datetime.now(tz=timezone.utc) - date).total_seconds()
        hours = int(delta // 3600)
        seconds = int(delta - (hours * 3600))
        delta_str = f'{hours} hours and {seconds} seconds ago'
        tb = ''.join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        response = [f'`Error occured {delta_str}`']

        if isinstance(error_source, commands.Context):
            guild = error_source.guild
            channel = error_source.channel
            response.append(
                f'`Server:{guild.name} | Channel: {channel.name}`' if guild else '`In DMChannel`'
            )
            response.append(
                f'`User: {error_source.author.name}#{error_source.author.discriminator}`'
            )
            response.append(f'`Command: {error_source.invoked_with}`')
            response.append(error_source.message.jump_url)
            e = Embed(title='Full command that caused the error:',
                      description=orig_content)
            e.set_footer(text=error_source.author.display_name,
                         icon_url=error_source.author.avatar_url)
        else:
            response.append(f'`Error caught in {error_source}`')
            e = None
        response.append(f'```python\n')
        num_chars = sum(len(line) for line in response)
        for line in tb.split('\n'):
            num_chars += len(line)
            response.append(line)
            if num_chars > 1800:
                response.append('```')
                await ctx.send('\n'.join(response))
                response = ['```python\n']
                num_chars = 0
        response.append('```')

        await ctx.send('\n'.join(response), embed=e)

    # @commands.command()
    # async def error_mock(self, ctx):
    #     print('MOCKING')
    #     raise CustomError('Mocked Test Error')

    # @commands.Cog.listener()
    # async def on_message_edit(self, before, after):
    #     if 'mock' in after.content:
    #         await self.client.process_commands(after)
    #         # ctx = await self.client.get_context(after)
    #         # await self.client.get_command('error_mock').invoke(ctx)


def setup(client):
    client.add_cog(ErrorHandler(client))
