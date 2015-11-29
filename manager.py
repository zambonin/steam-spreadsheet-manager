#!/usr/bin/env python

import csv
import gspread
import json
import locale
import re
import requests
import subprocess

from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials


def merge_dict_lists(list1, list2, key):
    merged = {}
    for item in list1 + list2:
        if item[key] in merged:
            merged[item[key]].update(item)
        else:
            merged[item[key]] = item
    return [value for (_, value) in merged.items()]


def show_icon(game):
    if "img_icon_url" in game.keys():
        return ("=IMAGE(\"http://media.steampowered.com/"
                "steamcommunity/public/images/"
                "apps/{}/{}.jpg\"; 1)").format(game['appid'],
                                               game['img_icon_url'])
    return ""


def price_paid(game):
    return locale.str(game['price_paid'])


def time_played(game):
    if "playtime_forever" in game.keys():
        return locale.str(game['playtime_forever'] / 60)
    return "0"


def price_per_hour(game):
    spent = locale.atof(time_played(game))
    paid = locale.atof(price_paid(game))
    if not spent:
        return 0
    if spent < 1:
        return locale.str(spent)
    return locale.str(paid / spent)


def discount_info(game):
    if not game['orig_price']:
        return 1
    fluct = abs((game['price_paid'] * 100 / game['orig_price']) - 1)
    return locale.str(fluct)


def achiev_info(game):
    url = ("http://api.steampowered.com/ISteamUserStats/"
           "GetPlayerAchievements/v0001/")
    data = requests.get(url, params={
                        "appid": str(game['appid']),
                        "key": api_key,
                        "steamid": steamid,
                        }).json()['playerstats']

    if data['success'] and 'achievements' in data.keys():
        cont = len([i for i in data['achievements'] if i['achieved']])
        game['achiev'] = cont / len(data['achievements'])
        return locale.str(game['achiev'])
    return ""


def prep_game_list():
    def read_steam_data():
        url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        return requests.get(url, params={
                            "key": api_key,
                            "steamid": steamid,
                            "include_played_free_games": 1,
                            "include_appinfo": 1,
                            }).json()['response']['games']

    def read_price_data(path):
        with open(path) as f:
            content = csv.reader(f)
            return [{'appid': int(line[0]), 'price_paid': float(line[1])}
                    for line in content]

    def read_license_data():
        cmd = "steamcmd +login {} +licenses_print +quit".format(
            steam_login).split()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        content = [i.decode() for i in proc.stdout]
        index = [i for i, line in enumerate(content) if "License" in line][1]

        return [{'package': int(re.findall(r'(\d+)', content[i])[0]),
                 'date': datetime.strptime(re.findall(
                     r'.* : (.+?) in .*', content[i+1])[0],
                     '%a %b %d %H:%M:%S %Y'),
                 'location': re.findall(r'"(.*?)"', content[i+1])[0],
                 'license': re.findall(r'.*\, (.*)', content[i+1])[0],
                 'apps': re.findall(r'(\d+)', content[i+2])[:-1]}
                for i in range(index, len(content), 4)]

    steam_data = read_steam_data()
    price_data = read_price_data('prices.csv')
    license_data = read_license_data()

    priced_games = merge_dict_lists(steam_data, price_data, 'appid')
    freeless = [i for i in priced_games if 'price_paid' in i.keys()]

    for g in freeless:
        for l in license_data:
            if str(g['appid']) in l['apps']:
                g['package'] = l['package']
                g['date'] = l['date'].strftime('%d/%m/%Y %H:%M:%S')
                g['location'] = l['location']
                g['license'] = l['license']
                break

    return sorted(freeless, key=lambda k: k['appid'])


private_data = json.load(open('config.json'))
api_key = private_data['api_key']
steamid = private_data['steamid']
steam_login = private_data['steam_login']

scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    private_data['json_keyfile_path'], scope)

gc = gspread.authorize(credentials)

game_list = prep_game_list()

locale.setlocale(locale.LC_ALL, '')
worksheet = gc.open_by_key(private_data['spreadsheet_key']).sheet1
index, length = 2, len(game_list)
worksheet.resize(length + (index - 1))
values_list = []

for game, i in zip(game_list, range(index, length + index)):
    url = "http://store.steampowered.com/api/appdetails/"
    raw = requests.get(url, params={"appids": str(game['appid'])}).json()
    data = raw[list(raw.keys())[0]]

    game['orig_price'] = game['price_paid']
    if data['success'] and "price_overview" in data['data'].keys():
        game['orig_price'] = data['data']['price_overview']['initial']

    if data['success'] and "name" not in game.keys():
        game['name'] = data['data']['name']

    values_list += [show_icon(game), game['appid'], game['name'],
                    price_paid(game), time_played(game), price_per_hour(game),
                    achiev_info(game), discount_info(game), game['package'],
                    game['date'], game['location'], game['license']]

    percentage = ((i - index + 1) / length)
    print("[{:2.1%}] Row #{}".format(percentage, i), end='\r')

print("Uploading to Google Drive...")
cell_list = worksheet.range('A{}:L{}'.format(index, length + index - 1))

for cell, value in zip(cell_list, values_list):
    cell.value = value
worksheet.update_cells(cell_list)
