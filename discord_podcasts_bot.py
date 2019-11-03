import os
import json
import logging
import traceback
import time

import asyncio
import discord
from discord.ext import commands
from threading import Thread

# local imports
import podcast_utils
from cogs.show import ShowCog
from cogs.caller import CallerCog
from cogs.error import ErrorCog


description = 'A Discord call-screening bot for live radio shows.'

dir_path = os.path.dirname(os.path.realpath(__file__))
print('dir_path: '+dir_path)
with open(dir_path+'/config.json', 'r') as f:
    config = json.load(f)

TOKEN = config['AUTH']['TOKEN']
CALLER_ROLE_ID = config['ROLES']['CALLER']['id']
SCREENING_CHANNEL_ID = config['CHANNELS']['SCREENING']['id']
SHOW_CHANNEL_ID = config['CHANNELS']['VOICE']['id']

# Below cogs represents our folder our cogs are in.
# Following is the file name. So 'meme.py' in cogs, would be cogs.meme
# Think of it like a dot path import
initial_extensions = ['cogs.error']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)


bot = commands.Bot(command_prefix='!', description=description)

show_helper = podcast_utils.show_helper(bot, config)

bot.add_cog(ErrorCog(bot))
bot.add_cog(ShowCog(bot, show_helper, config))
bot.add_cog(CallerCog(bot, show_helper, config))
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Bot Commands
# ------------------------------------------------------------------------------

@bot.event
async def on_ready():
    logging.info("Logged in as: %s", bot.user.name)
    logging.info('Version: %s', discord.__version__)
    logging.info('-' * 10)
    await show_helper.serverCheck()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the phones."))


@bot.event
async def on_voice_state_update(member, before, after):
    live_caller_role = discord.utils.find(lambda m: m.id == CALLER_ROLE_ID, member.guild.roles)
    screening_channel = discord.utils.find(lambda m: m.id == SCREENING_CHANNEL_ID, member.guild.channels)
    show_channel = discord.utils.find(lambda m: m.id == SHOW_CHANNEL_ID, member.guild.channels)
    is_live_caller = bool(live_caller_role is not None and member in live_caller_role.members)

    # If a Live Caller drops from a voice channel
    if after.channel != show_channel and is_live_caller:
        msg_user_voice = f"Live Caller '{show_helper.name(member)}' has dropped from the Live Show voice channel!"
        await screening_channel.send(msg_user_voice)
        return

    # If a Live Caller joines the voice channel
    if after.channel == show_channel and is_live_caller:
        msg_user_voice = f"Live Caller '{show_helper.name(member)}' has joined the Live Show voice channel!"
        await screening_channel.send(msg_user_voice)


bot.run(TOKEN, bot=True, reconnect=True)
