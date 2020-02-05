import logging
import asyncio
import discord
import os
import json

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(dir_path+'/config.json', 'r') as f:
    config = json.load(f)
    
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)


CALL_IN_CHANNEL_NAME = config['CHANNELS']['CALL_IN']['name']
CALL_IN_CHANNEL_ID = config['CHANNELS']['CALL_IN']['id']
NONLIVE_CHANNEL_NAME = config['CHANNELS']['NONLIVE']['name']
NONLIVE_CHANNEL_ID = config['CHANNELS']['NONLIVE']['id']
SCREENING_CHANNEL_NAME = config['CHANNELS']['SCREENING']['name']
SCREENING_CHANNEL_ID = config['CHANNELS']['SCREENING']['id']
SHOW_CHANNEL_NAME = config['CHANNELS']['VOICE']['name']
SHOW_CHANNEL_ID = config['CHANNELS']['VOICE']['id']
HOST_ROLE_ID = config['ROLES']['HOST']['id']
CALLER_ROLE_ID = config['ROLES']['CALLER']['id']


async def channel_check(bot):
    guild = bot.get_guild(config['SERVER']['ID'])

    global CALL_IN_CHANNEL_ID
    global NONLIVE_CHANNEL_ID
    global SCREENING_CHANNEL_ID
    global SHOW_CHANNEL_ID

    if bot.get_channel(CALL_IN_CHANNEL_ID) is None:
        logging.info("Call in Channel Missing")
        logging.info(guild.me)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649)),
            guild.me: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649))
        }
        call_in_channel = await guild.create_text_channel(CALL_IN_CHANNEL_NAME, overwrites=overwrites)
        CALL_IN_CHANNEL_ID = call_in_channel.id

    if bot.get_channel(NONLIVE_CHANNEL_ID) is None:
        logging.info("Non-live Channel Missing")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649))
        }
        non_live_channel = await guild.create_text_channel(NONLIVE_CHANNEL_NAME, overwrites=overwrites)
        NONLIVE_CHANNEL_ID = non_live_channel.id

    if bot.get_channel(SCREENING_CHANNEL_ID) is None:
        logging.info("Screening Channel Missing")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite().from_pair(discord.Permissions.none(), discord.Permissions.all()),
            guild.me: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649)),
            guild.get_role(HOST_ROLE_ID): discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649))
        }
        screening_channel = await guild.create_text_channel(SCREENING_CHANNEL_NAME, overwrites=overwrites)
        SCREENING_CHANNEL_ID = screening_channel.id

    if bot.get_channel(SHOW_CHANNEL_ID) is None:
        logging.info("Show Channel Missing")
        overwrites = {
            guild.default_role:discord.PermissionOverwrite().from_pair(discord.Permissions.none(), discord.Permissions.all()),
            guild.me: discord.PermissionOverwrite().from_pair(discord.Permissions(286262288), discord.Permissions().none()),
            guild.get_role(HOST_ROLE_ID): discord.PermissionOverwrite().from_pair(discord.Permissions(36701440), discord.Permissions().none()),
            guild.get_role(CALLER_ROLE_ID): discord.PermissionOverwrite().from_pair(discord.Permissions(36701184), discord.Permissions().none()), 
        }
        show_channel = await guild.create_voice_channel(SHOW_CHANNEL_NAME, overwrites=overwrites)
        SHOW_CHANNEL_ID = show_channel.id

    update_config_file_channel_ids()
    await add_bot_to_channel(bot)
    return
    
def update_config_file_channel_ids():
    # Need to update config file with new channels
    config['CHANNELS']['CALL_IN']['id'] = CALL_IN_CHANNEL_ID
    config['CHANNELS']['NONLIVE']['id'] = NONLIVE_CHANNEL_ID
    config['CHANNELS']['SCREENING']['id'] = SCREENING_CHANNEL_ID
    config['CHANNELS']['VOICE']['id'] = SHOW_CHANNEL_ID
    with open("config.json", "w") as jsonFile:
        json.dump(config, jsonFile)
    return
    
async def add_bot_to_channel(bot):
    bot_info = await bot.application_info()
    bot_user = bot.get_guild(config['SERVER']['ID']).get_member(bot_info.id)
    live_channel =bot.get_channel(config['CHANNELS']['VOICE']['id'])
    channel_roles = live_channel.overwrites
    for role in channel_roles:
        if role == bot_user.top_role:
            logging.info("Bot's role Already present on live Channel")
            return
    bot_perms = discord.PermissionOverwrite(
        manage_roles=True,
        manage_channels=True
    )
    await live_channel.set_permissions(bot_user.top_role, overwrite=bot_perms)
    return