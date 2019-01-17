import json
import logging
import traceback

import asyncio
import discord
from discord.ext import commands

import role_checker

description = 'A Discord call-screening bot for live radio shows.'

with open('config.json', 'r') as f:
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
HOST_ROLE_ID = config['ROLES']['HOST_ROLE_ID']
CALLER_ROLE_ID = config['ROLES']['LIVE_CALLER_ID']

# Below cogs represents our folder our cogs are in.
# Following is the file name. So 'meme.py' in cogs, would be cogs.meme
# Think of it like a dot path import
initial_extensions = ['cogs.error']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

bot = commands.Bot(command_prefix='!', description=description)

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

def is_in_channel(id):
    async def predicate(ctx):
        return isinstance(ctx.channel, discord.TextChannel) and ctx.message.channel.id == id
    return commands.check(predicate)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Other Methods - Non Commands
# ------------------------------------------------------------------------------

def name(member):
        # A helper function to return the member's display name
        nick = name = None
        try:
            nick = member.nick
        except AttributeError:
            pass

        try:
            name = member.name
        except AttributeError:
            pass

        if nick:
            return nick
        if name:
            return name
        return None

async def is_live_show_happening(ctx):
    show_channel = bot.get_channel(SHOW_CHANNEL_ID)
    members = show_channel.members
    member_ids = [member.id for member in members]

    # Check if at least one host is in the live channel
    hosts_in_channel = [host for host in HOST_IDS if host in member_ids]
    if len(hosts_in_channel) > 0:
        return True
    else:
        nonlive_channel = bot.get_channel(NONLIVE_CHANNEL_ID)
        nonlive_msg = f'{ctx.author.mention} There is currently no live show. Please post your question in {nonlive_channel.mention} for the next show!'
        await ctx.send(nonlive_msg)
        return False


def is_anyone_mentioned(ctx):
    try:
        mentioned_user = ctx.message.mentions[0]
    except:
        mentioned_user = None
    return mentioned_user


async def clean_and_add_livecallers(ctx, user=None):
    # Clean Live Callers of any stale users
    live_caller_role = discord.utils.find(lambda m: m.id == CALLER_ROLE_ID, ctx.guild.roles)
    logging.info('Found Live Caller Role - %s', live_caller_role)
    for member in live_caller_role.members:
        if member != user:
            msg_extra_live = f'FYI - I discovered that {member.name} was still in the Live Callers group while trying to add a new user. I have removed them now.'
            await ctx.send(msg_extra_live)
            await member.remove_roles(live_caller_role)

    # Add Requested User to Live Caller Role
    await user.add_roles(live_caller_role)


async def clean_livecallers(ctx):
    # Clean Live Callers of any stale users
    live_caller_role = discord.utils.find(lambda m: m.id == CALLER_ROLE_ID, ctx.guild.roles)
    logging.info('Found Live Caller Role - %s', live_caller_role)
    for member in live_caller_role.members:
        await member.remove_roles(live_caller_role)


async def gather_caller_info(author):
    # Implement wait_for check (is author & DM)
    def check(m):
        return m.author == author and isinstance(m.channel, discord.DMChannel)

    await author.send("Thanks for wanting to call in. Before we get you on the line, let's get a few details.")

    # Ask Question 1
    await author.send("What should we call you?")
    caller_name = await bot.wait_for('message', timeout=30, check=check)
    caller_name = caller_name.content

    # Ask Question 2
    await author.send(f'Hey {caller_name} - where are you from?')
    caller_location = await bot.wait_for('message', timeout=30, check=check)
    caller_location = caller_location.content

    # Ask Question 3
    await author.send(f'Thanks for that {caller_name} - what would you like to discuss?')
    caller_topic = await bot.wait_for('message', timeout=30, check=check)
    caller_topic = caller_topic.content

    # Send confirmation message
    caller_details = f'{caller_name} from {caller_location} wants to talk about - {caller_topic}'
    await author.send(f'We will send the following message to the live show screening channel.\n'
                                       f'`{caller_details}`\n\nIf this is correct, reply with the word YES.')
    caller_confirm = await bot.wait_for('message', timeout=30, check=check)

    if 'YES' in caller_confirm.content.upper():
        e = discord.Embed(title='NEW CALLER ALERT!', description=caller_details)
        # e.set_thumbnail(url=author.avatar_url)
        e.add_field(name='\a', value='\a', inline=False)    # Blank line (empty field)
        e.add_field(name='To add the caller:', value=f"!{config['COMMANDS']['answer']} {author.mention}", inline=False)
        e.add_field(name='To remove the caller:', value=f"!{config['COMMANDS']['answer']}", inline=False)

        screening_channel = bot.get_channel(SCREENING_CHANNEL_ID)
        await screening_channel.send(embed=e)
        await author.send('Awesome - thanks! Your message has been sent '
                          'and you will be notified when you are dialed into the live show!')


def role_check():
    logging.info("Checking if roles are available")
    are_roles_available, missing_roles = role_checker.find_roles([str(HOST_ROLE_ID), str(CALLER_ROLE_ID)])
    if are_roles_available:
        logging.info("All required roles are available")
        return
    else:
        logging.info("Server is missing roles: " + missing_roles)
        create_missing_roles(missing_roles)


def create_missing_roles(missing_roles):
    logging.info("Creating roles")
    # Here is were we'll handle creating anything that's missing

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# Bot Commands
# ------------------------------------------------------------------------------


@bot.event
async def on_ready():
    logging.info("Logged in as: %s", bot.user.name)
    logging.info('Version: %s', discord.__version__)
    logging.info('-' * 10)
    role_check()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the phones."))


@bot.event
async def on_voice_state_update(member, before, after):
    live_caller_role = discord.utils.find(lambda m: m.id == CALLER_ROLE_ID, member.guild.roles)
    screening_channel = discord.utils.find(lambda m: m.id == SCREENING_CHANNEL_ID, member.guild.channels)
    show_channel = discord.utils.find(lambda m: m.id == SHOW_CHANNEL_ID, member.guild.channels)
    is_live_caller = bool(member in live_caller_role.members)

    # If a Live Caller drops from a voice channel
    if after.channel != show_channel and is_live_caller:
        msg_user_voice = f"Live Caller '{name(member)}' has dropped from the Live Show voice channel!"
        await screening_channel.send(msg_user_voice)
        return

    # If a Live Caller joines the voice channel
    if after.channel == show_channel and is_live_caller:
        msg_user_voice = f"Live Caller '{name(member)}' has joined the Live Show voice channel!"
        await screening_channel.send(msg_user_voice)



@bot.command(name=config['COMMANDS']['call'])
@commands.cooldown(1, 30, commands.BucketType.user)
@is_in_channel(CALL_IN_CHANNEL_ID)
async def call(ctx):
    logging.info("Command '%s' detected in call-in channel (%s).", ctx.command.name, CALL_IN_CHANNEL_NAME)
    # Check if there is a Live Show in Progress
    if not await is_live_show_happening(ctx):
        return

    # If there is a live show in progress, get caller information
    try:
        await gather_caller_info(ctx.message.author)
    except asyncio.TimeoutError:
        await ctx.message.author.send(f"We haven't heard from you in a while."
                                      f"If you'd like to call back in, please issue the `!call` command again!")
        return


@bot.command(name=config['COMMANDS']['answer'])
@commands.has_role(HOST_ROLE_ID)
@is_in_channel(SCREENING_CHANNEL_ID)
async def answer(ctx):
    logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, SCREENING_CHANNEL_NAME)

    # Check if this command mentions anyone (invalid without a Member object)
    user = is_anyone_mentioned(ctx)
    if user is None:
        await ctx.send(f'{ctx.author.mention} you need to mention a user for this command to work properly.')
        return

    # Clean Live Callers & add requested user
    await clean_and_add_livecallers(ctx, user)

    # Check if user is listening to the live show
    show_channel = bot.get_channel(SHOW_CHANNEL_ID)
    live_listeners = show_channel.members
    if user in live_listeners:
        add_msg = f'{name(user)} has been added to the Live Caller role and can speak in the voice channel.'
        msg_user_notify = f'You are now connected to the live show!'
    else:
        add_msg = (f'{name(user)} has been added to the Live Caller role, but is not yet in the voice channel. '
                   f'I will let you know when they join.')
        msg_user_notify = (f'You are now connected to the live show!'
                           f'Please be sure you are connected to the {show_channel.mention} channel to talk.')

    # Send the Screening notification & User a DM for the live call-in
    await ctx.send(add_msg)
    await user.send(msg_user_notify)


@bot.command(name=config['COMMANDS']['hangup'])
@commands.has_role(HOST_ROLE_ID)
@is_in_channel(SCREENING_CHANNEL_ID)
async def hangup(ctx):
    logging.info("Command '%s' detected in call screening channel (%s).", ctx.command.name, SCREENING_CHANNEL_NAME)

    # Remove all members from the Live Callers role
    await clean_livecallers(ctx)

bot.run(TOKEN, bot=True, reconnect=True)
