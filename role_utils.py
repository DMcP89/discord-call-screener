import os
import json
import requests
import logging
import asyncio
import discord


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

def load_config():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(dir_path+'/client_config.json', 'r') as f:
        logging.info("ROLES UTILS LOADING client_config.json")
        config = json.load(f)
    return config

def check_if_roles_are_missing(config, roles):
    caller_found = False
    host_found = False
    for role in roles:
        if role.id == config['ROLES']['HOST']['id']:
            host_found = True
        elif role.id == config['ROLES']['CALLER']['id']:
            caller_found = True
    if caller_found and host_found:
        return {}
    else:
        return {'HOST': host_found, 'CALLER': caller_found}
        
        
        
async def role_check(bot):
    logging.info("Checking if roles are available")
    config = load_config()
    roles = bot.get_guild(config['GUILD']).roles
    missing_roles = check_if_roles_are_missing(config, roles)
    if missing_roles:
        logging.info("Roles are missing!")
        await create_missing_roles(missing_roles, bot, config)
    else:
        logging.info("All required roles are available")
        return

async def create_missing_roles(missing_roles, bot, config):
    logging.info("Creating roles...")
    # Here is were we'll handle creating anything that's missing
    for role in missing_roles:
        if not missing_roles[role]:
            role_name = config['ROLES'][role]['name']
            logging.info("Creating Role: " + role_name)
            if role == 'HOST':
                new_role = await bot.get_guild(config['GUILD']).create_role(name=role_name)
                config['ROLES']['HOST']['id'] = new_role.id
            else:
                new_role = await bot.get_guild(config['GUILD']).create_role(name=role_name)
                config['ROLES']['CALLER']['id'] = new_role.id
            update_config_file_role_ids(config)
    return

def update_config_file_role_ids(config):
    # Need to update config file with new roles
    config['ROLES']['HOST']['id'] = config['ROLES']['HOST']['id']
    config['ROLES']['CALLER']['id'] = config['ROLES']['CALLER']['id']
    with open("client_config.json", "w") as jsonFile:
        json.dump(config, jsonFile)
    return
# if __name__ == '__main__':
#     print(find_roles([str(458818918169968640), str(519697126557745153)]))
