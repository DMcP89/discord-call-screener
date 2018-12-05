import json
from call_screener import CallScreenerBot

with open('config.json', 'r') as f:
    config = json.load(f)

TOKEN = config['AUTH']['TOKEN']
CALL_IN_CHANNEL = config['CHANNELS']['CALL_IN']
SCREENING_CHANNEL = config['CHANNELS']['SCREENING']

call_screener = CallScreenerBot(TOKEN, CALL_IN_CHANNEL, SCREENING_CHANNEL)
call_screener.run()