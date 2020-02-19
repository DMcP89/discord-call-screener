import os
import sys
import getopt
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


config_file = '/client_config.json'
# print('dir_path: '+dir_path)
# with open(dir_path+config_file, 'r') as f:
#     config = json.load(f)

TOKEN = ''
CALLER_ROLE_ID = ''
SCREENING_CHANNEL_ID = ''
SHOW_CHANNEL_ID = ''

# Below cogs represents our folder our cogs are in.
# Following is the file name. So 'meme.py' in cogs, would be cogs.meme
# Think of it like a dot path import
initial_extensions = ['cogs.error']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)


bot = commands.Bot(command_prefix='!', description=description)

show_helper = None


def parse_options(opts):
    for opt, arg in opts:
        if opt == '-h':
            print('discord_podcast_bot -c <configfile>')
            sys.exit()
        elif opt in ("-c", "--conf"):
            global config_file
            config_file = arg
            

def load_config_file(config_file):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(dir_path+config_file, 'r') as f:
        config = json.load(f)
    set_globals(config)
    return config


def set_globals(config):
    global TOKEN
    TOKEN = config['TOKEN']
    global CALLER_ROLE_ID
    CALLER_ROLE_ID = config['ROLES']['CALLER']['id']
    global SCREENING_CHANNEL_ID
    SCREENING_CHANNEL_ID = config['CHANNELS']['SCREENING']['id']
    global SHOW_CHANNEL_ID
    SHOW_CHANNEL_ID = config['CHANNELS']['VOICE']['id']


def main(argv):
    try:
        opts, args = getopt.getopt(argv,"hc:",["conf="])
    except getopt.GetoptError:
        print('discord_podcast_bot -c <configfile>')
        sys.exit(2)
    parse_options(opts)
    config  = load_config_file(config_file)
    global show_helper
    show_helper = podcast_utils.show_helper(bot, config)
    if not discord.opus.is_loaded():
            discord.opus.load_opus('libopus.so.0')
    bot.add_cog(ErrorCog(bot))
    bot.add_cog(ShowCog(bot, show_helper, config))
    bot.add_cog(CallerCog(bot, show_helper, config))
    bot.run(TOKEN, bot=True, reconnect=True)

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

if __name__ == "__main__":
    main(sys.argv[1:])