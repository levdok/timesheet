import re
from configparser import SafeConfigParser

import arrow
import pandas as pd
import requests

SETTINGS_FILE = 'settings.ini'
TOGGL_URL = 'https://www.toggl.com/api/v8/time_entries'
TEMPO_URL = 'https://api.tempo.io/core/3/worklogs'
JIRA_REGEXP = re.compile(r'[A-Za-z]{2,5}-\d+')
END_TIME = arrow.utcnow().to('Europe/Moscow').format('YYYY-MM-DDTHH:mm:ssZZ')

CONFIG = SafeConfigParser()
CONFIG.read(SETTINGS_FILE)

params = {'start_date': CONFIG.get('tempo', 'lastSuccessful'), 'end_date': END_TIME}

toggl_response = requests.get(TOGGL_URL, auth=(CONFIG.get('toggl', 'token'), 'api_token'), params=params)

df = pd.DataFrame(toggl_response.json())
df['date'] = df.apply(lambda row: (arrow.get(row.start)).date().isoformat(), axis=1)
grouped = df.groupby(['description', 'date']).agg({'start': 'min', 'duration': 'sum'})[['start', 'duration']].reset_index()
collapsed_data = grouped.to_dict('r')

for task in collapsed_data:
    key = ''
    if JIRA_REGEXP.search(task.get('description')):
        key = JIRA_REGEXP.search(task.get('description')).group()
    else:
        key = CONFIG.get('tempo', 'defaultKey')

    start_date = task.get('date')
    start_time = arrow.get(task.get('start')).time().isoformat()
    description = ''
    if not description:
        description = CONFIG.get('tempo', 'defaultDescription')
    else:
        description = task.get('description').replace(key, '').strip()

    data = {
        'issueKey': key,
        'timeSpentSeconds': task.get('duration'),
        'startDate': start_date,
        'startTime': start_time,
        'description': description,
        'authorAccountId': CONFIG.get('authorAccountId'),
    }

    requests.post(
        TEMPO_URL, json=data, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + CONFIG.get('tempo', 'token')}
    )

CONFIG.set('tempo', 'lastSuccessful', END_TIME)

    with open('settings.ini', 'wb') as file:
    CONFIG.write(file)

print('done')
