import json
import requests

with open('config.json', 'r') as f:
    config = json.load(f)

TOKEN = config['AUTH']['TOKEN']
SERVER_ID = config['SERVER']['ID']


def get_roles_from_server():
    url = 'https://discordapp.com/api/guilds/'+str(SERVER_ID)+'/roles'
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Rigor/1.0.0; http://rigor.com)',
        'Authorization': 'Bot '+TOKEN
    }
    response = requests.get(url, headers=headers)
    roles_data = json.loads(response.text)
    return roles_data


def find_roles(target_roles):
    found_roles = []
    for role in get_roles_from_server():
        if role["id"] in target_roles:
            found_roles.append(role["id"])
            target_roles.remove(role["id"])

    if len(target_roles) == 0:
        return True, target_roles
    else:
        return False, target_roles

# if __name__ == '__main__':
#     print(find_roles([str(458818918169968640), str(519697126557745153)]))
