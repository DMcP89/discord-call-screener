import discord
import logging
import asyncio
import os
import json
import podcast_utils
from discord.ext import commands

dir_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.dirname(dir_path)+'/config.json', 'r') as f:
    config = json.load(f)

class CallerCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.helper = podcast_utils.show_helper(bot, config)

    @commands.command(name='call')
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def call(self,ctx):
        logging.info("Command '%s' detected in call-in channel (%s).", ctx.command.name, config['CHANNELS']['CALL_IN']['name'])
        # Check if there is a Live Show in Progress
        if not await self.helper.is_live_show_happening(ctx):
            return
        # If there is a live show in progress, get caller information
        try:
            await self.helper.gather_caller_info(ctx.message.author)
        except asyncio.TimeoutError:
            await ctx.message.author.send(f"We haven't heard from you in a while."
                                        f"If you'd like to call back in, please issue the `!call` command again!")
            return
    
    @commands.command(name='answer')
    @commands.has_role(config['ROLES']['HOST']['id'])
    async def answer(self,ctx):
        logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, config['CHANNELS']['SCREENING']['name'])

        # Check if this command mentions anyone (invalid without a Member object)
        user = self.helper.is_anyone_mentioned(ctx)
        if user is None:
            await ctx.send(f'{ctx.author.mention} you need to mention a user for this command to work properly.')
            return

        # Clean Live Callers & add requested user
        await self.helper.clean_and_add_livecallers(ctx, user)

        # Check if user is listening to the live show
        show_channel = self.bot.get_channel(config['CHANNELS']['VOICE']['id'])
        live_listeners = show_channel.members
        if user in live_listeners:
            add_msg = f'{self.helper.name(user)} has been added to the Live Caller role and can speak in the voice channel.'
            msg_user_notify = f'You are now connected to the live show!'
        else:
            add_msg = (f'{self.helper.name(user)} has been added to the Live Caller role, but is not yet in the voice channel. '
                    f'I will let you know when they join.')
            msg_user_notify = (f'You are now connected to the live show!'
                            f'Please be sure you are connected to the {show_channel.mention} channel to talk.')

        # Send the Screening notification & User a DM for the live call-in
        await ctx.send(add_msg)
        await user.send(msg_user_notify)

    @commands.command(name='hangup')
    @commands.has_role(config['ROLES']['HOST']['id'])
    async def hangup(self,ctx):
        logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, config['CHANNELS']['SCREENING']['name'])
        # Remove all members from the Live Callers role
        await self.helper.clean_livecallers(ctx)

def setup(bot):
    bot.add_cog(CallerCog(bot))