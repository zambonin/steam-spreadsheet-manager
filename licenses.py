import datetime
import re

games = []
with open('licenses.txt') as f:
    data = f.readlines()
    for i in range(0, len(data), 4):
        games.append({
            'package': int(re.findall(r'(\d+)', data[i])[0]),
            'date': datetime.datetime.strptime(re.findall(
                r'.* : (.+?) in .*', data[i+1])[0], '%a %b %d %H:%M:%S %Y'),
            'location': re.findall(r'"(.*?)"', data[i+1])[0],
            'license': re.findall(r'.*\, (.*)', data[i+1])[0],
            'apps': re.findall(r'(\d+)', data[i+2])[:-1],
        })
