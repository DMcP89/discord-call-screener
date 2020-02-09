import logging
import asyncio
import discord
import os
import json



logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

def load_config():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(dir_path+'/client_config.json', 'r') as f:
        logging.info("CHANNEL_UTILS LOADING client_config.json")
        config = json.load(f)
    return config

async def channel_check(bot):
    config = load_config()
    guild = bot.get_guild(config['GUILD'])

    if bot.get_channel(config['CHANNELS']['CALL_IN']['id']) is None:
        logging.info("Call in Channel Missing")
        logging.info(guild.me)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649)),
            guild.me: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649))
        }
        call_in_channel = await guild.create_text_channel(config['CHANNELS']['CALL_IN']['name'], overwrites=overwrites)
        config['CHANNELS']['CALL_IN']['id'] = call_in_channel.id

    if bot.get_channel(config['CHANNELS']['NONLIVE']['id']) is None:
        logging.info("Non-live Channel Missing")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649))
        }
        non_live_channel = await guild.create_text_channel(config['CHANNELS']['NONLIVE']['name'], overwrites=overwrites)
        config['CHANNELS']['NONLIVE']['id'] = non_live_channel.id

    if bot.get_channel(config['CHANNELS']['SCREENING']['id']) is None:
        logging.info("Screening Channel Missing")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite().from_pair(discord.Permissions.none(), discord.Permissions.all()),
            guild.me: discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649)),
            guild.get_role(config['ROLES']['HOST']['id']): discord.PermissionOverwrite().from_pair(discord.Permissions(384064), discord.Permissions(805445649))
        }
        screening_channel = await guild.create_text_channel(config['CHANNELS']['SCREENING']['name'], overwrites=overwrites)
        config['CHANNELS']['SCREENING']['id'] = screening_channel.id

    if bot.get_channel(config['CHANNELS']['VOICE']['id']) is None:
        logging.info("Show Channel Missing")
        overwrites = {
            guild.default_role:discord.PermissionOverwrite().from_pair(discord.Permissions.none(), discord.Permissions.all()),
            guild.me: discord.PermissionOverwrite().from_pair(discord.Permissions(286262288), discord.Permissions().none()),
            guild.get_role(config['ROLES']['HOST']['id']): discord.PermissionOverwrite().from_pair(discord.Permissions(36701440), discord.Permissions().none()),
            guild.get_role(config['ROLES']['CALLER']['id']): discord.PermissionOverwrite().from_pair(discord.Permissions(36701184), discord.Permissions().none()), 
        }
        show_channel = await guild.create_voice_channel(config['CHANNELS']['VOICE']['name'], overwrites=overwrites)
        config['CHANNELS']['VOICE']['id'] = show_channel.id

    update_config_file_channel_ids(config)
    await add_bot_to_channel(bot, config)
    return
    
def update_config_file_channel_ids(config):
    # Need to update config file with new channels
    config['CHANNELS']['CALL_IN']['id'] = config['CHANNELS']['CALL_IN']['id']
    config['CHANNELS']['NONLIVE']['id'] = config['CHANNELS']['NONLIVE']['id']
    config['CHANNELS']['SCREENING']['id'] = config['CHANNELS']['SCREENING']['id']
    config['CHANNELS']['VOICE']['id'] = config['CHANNELS']['VOICE']['id']
    with open("client_config.json", "w") as jsonFile:
        json.dump(config, jsonFile)
    return
    
async def add_bot_to_channel(bot, config):
    bot_info = await bot.application_info()
    bot_user = bot.get_guild(config['GUILD']).get_member(bot_info.id)
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