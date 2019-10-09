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
import role_utils
import recording_utils
import channel_utils
import podcast_utils
import s3

description = 'A Discord call-screening bot for live radio shows.'

dir_path = os.path.dirname(os.path.realpath(__file__))
print('dir_path: '+dir_path)
with open(dir_path+'/config.json', 'r') as f:
    config = json.load(f)

TOKEN = config['AUTH']['TOKEN']
CALL_IN_CHANNEL_NAME = config['CHANNELS']['CALL_IN']['name']
CALL_IN_CHANNEL_ID = config['CHANNELS']['CALL_IN']['id']
NONLIVE_CHANNEL_NAME = config['CHANNELS']['NONLIVE']['name']
NONLIVE_CHANNEL_ID = config['CHANNELS']['NONLIVE']['id']
SCREENING_CHANNEL_NAME = config['CHANNELS']['SCREENING']['name']
SCREENING_CHANNEL_ID = config['CHANNELS']['SCREENING']['id']
SHOW_CHANNEL_NAME = config['CHANNELS']['VOICE']['name']
SHOW_CHANNEL_ID = config['CHANNELS']['VOICE']['id']

HOST_IDS = config['HOSTS']
HOST_ROLE_ID = config['ROLES']['HOST']['id']
CALLER_ROLE_ID = config['ROLES']['CALLER']['id']

# Below cogs represents our folder our cogs are in.
# Following is the file name. So 'meme.py' in cogs, would be cogs.meme
# Think of it like a dot path import
initial_extensions = ['cogs.error']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

bot = commands.Bot(command_prefix='!', description=description)

recording_thread = None
recording_buffer = recording_utils.BufSink()

show_helper = podcast_utils.show_helper(bot, config)

# Here we load our extensions(cogs) listed above in [initial_extensions].
if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            logging.error("Failed to load extension %s.", extension)
            traceback.print_exc()


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Helper Check Decorators
# ------------------------------------------------------------------------------

def is_in_channel(channel_name):
    async def predicate(ctx):
        if channel_name == CALL_IN_CHANNEL_NAME:
            return isinstance(ctx.channel, discord.TextChannel) and ctx.message.channel.id == CALL_IN_CHANNEL_ID
        elif channel_name == SCREENING_CHANNEL_NAME:
            return isinstance(ctx.channel, discord.TextChannel) and ctx.message.channel.id == SCREENING_CHANNEL_ID

    return commands.check(predicate)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Recording methods
# ------------------------------------------------------------------------------


def start_recordiing(show_channel):
    global recording_thread
    recording_filename = show_channel.name + "-" +time.strftime("%Y%m%d-%H%M%S")+ ".wav"
    if recording_thread is None:
        recording_thread = Thread(target=recording_utils.poster, args=(bot, recording_buffer, recording_filename))
        recording_thread.start()   
    bot.voice_clients[0].listen(recording_buffer)
    return   
    
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


@bot.command(name=config['COMMANDS']['call'])
@commands.cooldown(1, 30, commands.BucketType.user)
@is_in_channel(CALL_IN_CHANNEL_NAME)
async def call(ctx):
    logging.info("Command '%s' detected in call-in channel (%s).", ctx.command.name, CALL_IN_CHANNEL_NAME)
    # Check if there is a Live Show in Progress
    if not await show_helper.is_live_show_happening(ctx):
        return

    # If there is a live show in progress, get caller information
    try:
        await show_helper.gather_caller_info(ctx.message.author)
    except asyncio.TimeoutError:
        await ctx.message.author.send(f"We haven't heard from you in a while."
                                      f"If you'd like to call back in, please issue the `!call` command again!")
        return


@bot.command(name=config['COMMANDS']['answer'])
@commands.has_role(HOST_ROLE_ID)
@is_in_channel(SCREENING_CHANNEL_NAME)
async def answer(ctx):
    logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, SCREENING_CHANNEL_NAME)

    # Check if this command mentions anyone (invalid without a Member object)
    user = show_helper.is_anyone_mentioned(ctx)
    if user is None:
        await ctx.send(f'{ctx.author.mention} you need to mention a user for this command to work properly.')
        return

    # Clean Live Callers & add requested user
    await show_helper.clean_and_add_livecallers(ctx, user)

    # Check if user is listening to the live show
    show_channel = bot.get_channel(SHOW_CHANNEL_ID)
    live_listeners = show_channel.members
    if user in live_listeners:
        add_msg = f'{show_helper.name(user)} has been added to the Live Caller role and can speak in the voice channel.'
        msg_user_notify = f'You are now connected to the live show!'
    else:
        add_msg = (f'{show_helper.name(user)} has been added to the Live Caller role, but is not yet in the voice channel. '
                   f'I will let you know when they join.')
        msg_user_notify = (f'You are now connected to the live show!'
                           f'Please be sure you are connected to the {show_channel.mention} channel to talk.')

    # Send the Screening notification & User a DM for the live call-in
    await ctx.send(add_msg)
    await user.send(msg_user_notify)


@bot.command(name=config['COMMANDS']['hangup'])
@commands.has_role(HOST_ROLE_ID)
@is_in_channel(SCREENING_CHANNEL_NAME)
async def hangup(ctx):
    logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, SCREENING_CHANNEL_NAME)

    # Remove all members from the Live Callers role
    await show_helper.clean_livecallers(ctx)


@bot.command(name=config['COMMANDS']['start'])
@commands.has_role(HOST_ROLE_ID)
@is_in_channel(SCREENING_CHANNEL_NAME)
async def start_show(ctx):
    logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, SCREENING_CHANNEL_NAME)
    await show_helper.serverCheck()
    perms = discord.PermissionOverwrite(
        connect=True,
        speak=False,
        mute_members=False,
        deafen_members=False,
        move_members=False,
        use_voice_activation=False,
        priority_speaker=False,
        read_messages=True
    )
    await bot.get_channel(config['CHANNELS']['VOICE']['id']).set_permissions(ctx.guild.default_role, overwrite=perms)
    await bot.get_channel(SHOW_CHANNEL_ID).connect()
    start_recordiing(bot.get_channel(SHOW_CHANNEL_ID))


@bot.command(name=config['COMMANDS']['end'])
@commands.has_role(HOST_ROLE_ID)
@is_in_channel(SCREENING_CHANNEL_NAME)
async def end_show(ctx):
    logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, SCREENING_CHANNEL_NAME)
    perms = discord.PermissionOverwrite(
        connect=False,
        speak=False,
        mute_members=False,
        deafen_members=False,
        move_members=False,
        use_voice_activation=False,
        priority_speaker=False,
        read_messages=False
    )
    await bot.get_channel(config['CHANNELS']['VOICE']['id']).set_permissions(ctx.guild.default_role, overwrite=perms)
    await show_helper.clean_livecallers(ctx)
    if bot.voice_clients:
        for vc in bot.voice_clients:
            await vc.disconnect()
        recording_utils.recording_finished_flag = True
        global recording_thread
        recording_thread.join()
        s3.save_recording_to_bucket("discord-recordings-dev", recording_utils.recording_filename)

bot.run(TOKEN, bot=True, reconnect=True)
