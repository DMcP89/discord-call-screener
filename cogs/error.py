import discord
import logging
from discord.ext import commands

class ErrorCog:
    def __init__(self, bot):
        self.bot = bot

    async def on_command_error(self, ctx, error):
        """The event triggered when an error is raised while invoking a command.
        ctx   : Context
        error : Exception"""

        if hasattr(ctx.command, 'on_error'):
            return

        ignored = (commands.CommandNotFound, commands.UserInputError)
        error = getattr(error, 'original', error)

        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
            except:
                pass

        elif isinstance(error, commands.CheckFailure):
            logging.warning("%s tried to use the '%s' command, but a check failed. %s %s", ctx.author, ctx.command, ctx.message.guild, error)
            return

        elif isinstance(error, commands.CommandOnCooldown):
            logging.info("The command '%s' is on cooldown. Try again in %s seconds.", ctx.command, error.retry_after)
            return

def setup(bot):
    bot.add_cog(ErrorCog(bot))