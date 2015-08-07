#!/usr/bin/env python

import json
import os
import re
import requests
import subprocess

from datetime import datetime

before = datetime.now()

private_data = json.load(open('config.json'))
api_key = private_data['api_key']
steamid = private_data['steamid']
steam_login = private_data['steam_login']

url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/" + \
    "?key="+api_key+"&steamid=" + steamid + \
    "&include_appinfo=1&include_played_free_games=1"

response = requests.get(url).json()['response']['games']

for i in response:
    i.pop("playtime_2weeks", None)
    i.pop("has_community_visible_stats", None)
    i.pop("img_logo_url", None)

prices = []
with open('prices.csv') as f:
    data = f.readlines()
    for line in data:
        content = line.strip('\n').split(',')
        prices.append({
            'appid': int(content[0]),
            'price_paid': float(content[1]),
            })

intersec = list(set(i['appid'] for i in response) -
                set(i['appid'] for i in prices))

freeless = [i for i in response if i['appid'] not in intersec]

for i in freeless:
    for j in prices:
        if i['appid'] == j['appid']:
            i['price_paid'] = j['price_paid']
            prices.remove(j)

part_list = sorted(freeless + prices, key=lambda k: k['appid'])

bashCommand = "steamcmd +login " + steam_login + \
              " +licenses_print +quit > licenses.txt"
process = subprocess.Popen(bashCommand, shell=True, stdout=subprocess.PIPE)
license_info = []
with open('licenses.txt') as f:
    data = f.readlines()
    index = 0
    for i in range(len(data)):
        if "License" in data[i]:
            index = i
            break

    for i in range(index, len(data), 4):
        if "License" in data[i]:
            license_info.append({
                'package': int(re.findall(r'(\d+)', data[i])[0]),
                'date': datetime.strptime(re.findall(
                        r'.* : (.+?) in .*', data[i+1])[0],
                        '%a %b %d %H:%M:%S %Y'),
                'location': re.findall(r'"(.*?)"', data[i+1])[0],
                'license': re.findall(r'.*\, (.*)', data[i+1])[0],
                'apps': re.findall(r'(\d+)', data[i+2])[:-1],
                })

for game, count in zip(part_list, range(len(part_list))):
    raw_data = requests.get("http://store.steampowered.com/api/" +
                            "appdetails/?appids=" + str(game['appid'])).json()
    data = raw_data[list(raw_data.keys())[0]]

    game['orig_price'] = game['price_paid']
    if data['success'] and "price_overview" in list(data['data'].keys()):
        game['orig_price'] = data['data']['price_overview']['initial']

    if data['success'] and "name" not in list(game.keys()):
        game['name'] = data['data']['name']

    for i in license_info[1:]:
        if str(game['appid']) in i['apps']:
            game['package'] = i['package']
            game['date'] = i['date'].strftime('%d/%m/%Y %H:%M:%S')
            game['location'] = i['location']
            game['license'] = i['license']

    data = requests.get("http://api.steampowered.com/ISteamUserStats/" +
                        "GetPlayerAchievements/v0001/?appid=" +
                        str(game['appid']) + "&key=" + api_key + "&steamid=" +
                        steamid).json()['playerstats']

    game['achiev'] = ""
    if data['success'] and 'achievements' in data.keys():
        cont = len([i for i in data['achievements'] if i['achieved']])
        game['achiev'] = cont / len(data['achievements'])

    n = str(game['appid']) + ".in"
    os.makedirs("temp", exist_ok=True)
    with open("temp/" + n, 'w') as f:
        print("[{:2.1%}] ".format(count/len(part_list))+"Writing "+n, end="\r")
        json.dump(game, f, indent=4)

print('[100%] Time spent on updating:', str(datetime.now() - before))
