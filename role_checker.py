import json
import requests

with open('config.json', 'r') as f:
    config = json.load(f)

TOKEN = config['AUTH']['TOKEN']
SERVER_ID = config['SERVER']['ID']
ROLES = config['ROLES']


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

# if __name__ == '__main__':
#     print(find_roles([str(458818918169968640), str(519697126557745153)]))
