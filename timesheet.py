import requests
import re
from ConfigParser import SafeConfigParser
import arrow
import pandas as pd

settings_ini = 'settings.ini'
toggl_url = 'https://www.toggl.com/api/v8/time_entries'
tempo_url = 'https://api.tempo.io/core/3/worklogs'
jira_pattern = r'[A-Za-z]{2,5}-\d+'
end_time = arrow.utcnow().to('Europe/Moscow').format('YYYY-MM-DDTHH:mm:ssZZ')

config = SafeConfigParser()
config.read(settings_ini)

params = {'start_date': config.get('tempo', 'lastSuccessful'),
          'end_date': end_time}

toggl_response = requests.get(toggl_url, auth=(config.get('toggl', 'token'), 'api_token'), params=params)

df = pd.DataFrame(toggl_response.json())
df['date'] = df.apply(lambda row: (arrow.get(row.start)).date().isoformat(), axis=1)
grouped = df.groupby(['description', 'date']).agg({'start': 'min', 'duration': 'sum'})[
    ['start', 'duration']].reset_index()
collapsed_data = grouped.to_dict('r')

for task in collapsed_data:
    key = ''
    if re.search(jira_pattern, task.get('description')):
        key = re.search(jira_pattern, task.get('description')).group()
    else:
        key = config.get('tempo', 'defaultKey')

    start_date = task.get('date')
    start_time = arrow.get(task.get('start')).time().isoformat()
    description = ''
    if not description:
        description = config.get('tempo', 'defaultDescription')
    else:
        description = task.get('description').replace(key, '').strip()

    data = {'issueKey': key, 'timeSpentSeconds': task.get('duration'), 'startDate': start_date,
            'startTime': start_time, 'description': description, 'authorAccountId': config.get('authorAccountId')}

    requests.post(tempo_url, json=data, headers={'Content-Type': 'application/json',
                                                 'Authorization': 'Bearer ' + config.get('tempo', 'token')})

config.set('tempo', 'lastSuccessful', end_time)
with open('settings.ini', 'wb') as configfile:
    config.write(configfile)
print('done')
