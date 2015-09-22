#!/usr/bin/env python

import csv
import datetime
import gspread
import json
import locale
import re
import requests
import subprocess

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
        return "=IMAGE(\"http://media.steampowered.com/steamcommunity/" + \
            "public/images/apps/%d/%s.jpg\"; 1)" % (game['appid'],
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
    url = "http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
    data = requests.get(url, params={
                                "appid": str(game['appid']),
                                "key": api_key,
                                "steamid": steamid,
                            }).json()['playerstats']

    game['achiev'] = ""
    if data['success'] and 'achievements' in data.keys():
        cont = len([i for i in data['achievements'] if i['achieved']])
        game['achiev'] = cont / len(data['achievements'])

    if type(game['achiev']) == str:
        return ""
    return locale.str(game['achiev'])


def license_info(game):
    for each in license_data:
        if str(game['appid']) in each['apps']:
            game['package'] = each['package']
            game['date'] = each['date'].strftime('%d/%m/%Y %H:%M:%S')
            game['location'] = each['location']
            game['license'] = each['license']
    return game


def read_steam_data():
    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    return requests.get(url, params={
                                "key": api_key,
                                "steamid": steamid,
                                "include_played_free_games": 1,
                                "include_appinfo": 1,
                            }).json()['response']['games']


def read_price_data(path):
    prices = []
    with open(path) as f:
        content = csv.reader(f)
        for line in content:
            prices.append({
                'appid': int(line[0]),
                'price_paid': float(line[1]),
            })

    return prices


def read_license_data():
    bashCommand = "steamcmd +login " + steam_login + \
              " +licenses_print +quit > licenses.txt"
    subprocess.Popen(bashCommand, shell=True, stdout=subprocess.PIPE)
    license_info = []
    with open('licenses.txt') as f:
        data = f.readlines()
        index = 0
        for i in range(len(data)):
            if "License" in data[i]:
                index = i+4
                break

        for i in range(index, len(data), 4):
            if "License" in data[i]:
                license_info.append({
                    'package': int(re.findall(r'(\d+)', data[i])[0]),
                    'date': datetime.datetime.strptime(re.findall(
                                r'.* : (.+?) in .*', data[i+1])[0],
                                '%a %b %d %H:%M:%S %Y'),
                    'location': re.findall(r'"(.*?)"', data[i+1])[0],
                    'license': re.findall(r'.*\, (.*)', data[i+1])[0],
                    'apps': re.findall(r'(\d+)', data[i+2])[:-1],
                })

    return license_info


def exclude_free_games(game_list):
    for game in game_list:
        if 'price_paid' not in game.keys():
            game_list.remove(game)
    return game_list

private_data = json.load(open('config.json'))
api_key = private_data['api_key']
steamid = private_data['steamid']
steam_login = private_data['steam_login']

scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    private_data['json_keyfile_path'], scope)

gc = gspread.authorize(credentials)

prices = read_price_data('prices.csv')
game_data = read_steam_data()
game_list = exclude_free_games(sorted(merge_dict_lists(
    game_data, prices, 'appid'), key=lambda k: k['appid']))
license_data = read_license_data()

locale.setlocale(locale.LC_ALL, '')
worksheet = gc.open_by_key(private_data['spreadsheet_key']).sheet1
index = 2
worksheet.resize(len(game_list) + (index - 1))
values_list = []

for game, i in zip(game_list, range(index, len(game_list) + index)):
    game = license_info(game)

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

    percentage = (i - index + 1) / len(game_list)
    print("[{:2.1%}] ".format((i - index + 1) / len(game_list)) +
          "Row #%d" % i, end='\r')

print("Uploading to Google Drive...")
cell_list = worksheet.range('A%d:L%d' % (index, len(game_list) + (index - 1)))

for cell, value in zip(cell_list, values_list):
    cell.value = value
worksheet.update_cells(cell_list)
