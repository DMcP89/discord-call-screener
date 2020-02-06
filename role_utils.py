import os
import json
import requests
import logging
import asyncio
import discord

dir_path = os.path.dirname(os.path.realpath(__file__))

with open(dir_path+'/client_config.json', 'r') as f:
    config = json.load(f)

TOKEN = config['TOKEN']
SERVER_ID = config['GUILD']
ROLES = config['ROLES']

HOST_ROLE_ID = config['ROLES']['HOST']['id']
CALLER_ROLE_ID = config['ROLES']['CALLER']['id']

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)



def get_roles_from_server():
    url = 'https://discordapp.com/api/guilds/'+str(SERVER_ID)+'/roles'
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Rigor/1.0.0; http://rigor.com)',
        'Authorization': 'Bot '+TOKEN
    }
    response = requests.get(url, headers=headers)
    roles_data = json.loads(response.text)
    return roles_data


def find_roles():
    caller_found = False
    host_found = False
    for role in get_roles_from_server():
        if role['id'] == str(ROLES['HOST']['id']):
            host_found = True
        elif role['id'] == str(ROLES['CALLER']['id']):
            caller_found = True
    if caller_found and host_found:
        return {}
    else:
        return {'HOST': host_found, 'CALLER': caller_found}
        
        
        
async def role_check(bot):
    logging.info("Checking if roles are available")
    missing_roles = find_roles()
    if missing_roles:
        logging.info("Roles are missing!")
        await create_missing_roles(missing_roles, bot)
    else:
        logging.info("All required roles are available")
        return

async def create_missing_roles(missing_roles, bot):
    logging.info("Creating roles...")
    # Here is were we'll handle creating anything that's missing
    print(missing_roles)
    for role in missing_roles:
        print(missing_roles[role])
        if not missing_roles[role]:
            role_name = config['ROLES'][role]['name']
            logging.info("Creating Role: " + role_name)
            if role == 'HOST':
                perms = discord.PermissionOverwrite(
                    connect=True,
                    speak=True,
                    mute_members=True,
                    deafen_members=True,
                    move_members=True,
                    use_voice_activation=True,
                    priority_speaker=True,
                    read_messages=True
                )
                new_role = await bot.get_guild(config['GUILD']).create_role(name=role_name)
                global HOST_ROLE_ID
                HOST_ROLE_ID = new_role.id
            else:
                perms = discord.PermissionOverwrite(
                    connect=True,
                    speak=True,
                    mute_members=False,
                    deafen_members=False,
                    move_members=False,
                    use_voice_activation=True,
                    priority_speaker=False,
                    read_messages=True
                )
                new_role = await bot.get_guild(config['GUILD']).create_role(name=role_name)
                global CALLER_ROLE_ID
                CALLER_ROLE_ID = new_role.id
            update_config_file_role_ids()
    return

def update_config_file_role_ids():
    # Need to update config file with new roles
    config['ROLES']['HOST']['id'] = HOST_ROLE_ID
    config['ROLES']['CALLER']['id'] = CALLER_ROLE_ID
    with open("config.json", "w") as jsonFile:
        json.dump(config, jsonFile)
    return
# if __name__ == '__main__':
#     print(find_roles([str(458818918169968640), str(519697126557745153)]))
