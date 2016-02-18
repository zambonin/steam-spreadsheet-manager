#!/usr/bin/env python

import json

from csv import reader as creader
from datetime import datetime
from gspread import authorize as login
from multiprocessing.dummy import Pool as ThreadPool
from oauth2client.service_account import ServiceAccountCredentials
from re import findall
from requests import get as rget
from subprocess import Popen, PIPE
from urllib.parse import urlencode


def prep_game_list():
    def merge_dict_lists(list1, list2, key):
        merged = {}
        for item in list1 + list2:
            if item[key] in merged:
                merged[item[key]].update(item)
            else:
                merged[item[key]] = item
        return [value for (_, value) in merged.items()]

    def read_steam_data():
        url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        master = rget(url, params={
                      "key": api_key,
                      "steamid": steamid,
                      "include_played_free_games": 1,
                      "include_appinfo": 1,
                      }).json()['response']['games']

        base_url = ("http://api.steampowered.com/ISteamUserStats/"
                    "GetPlayerAchievements/v0001/?{}")
        urls = [base_url.format(urlencode({
                                "appid": game,
                                "key": api_key,
                                "steamid": steamid,
                                })) for game in [i['appid'] for i in master]]

        pool = ThreadPool(len(urls))

        results = pool.map(rget, urls)
        pool.close()
        pool.join()

        achiev_data = [i for i in [j.json()['playerstats'] for j in results]
                       if i['success'] and 'achievements' in i.keys()]

        final_dict = [{'name': i['gameName'],
                       'achiev': len([a for a in i['achievements']
                                     if a['achieved']])/len(i['achievements'])
                       } for i in achiev_data]

        return merge_dict_lists(master, final_dict, 'name')

    def read_price_data(path):
        return [{'name': line[1],
                 'appid': int(line[0]),
                 'price_paid': float(line[3]),
                 'orig_price': float(line[2])
                 } for line in creader(open(path))]

    def read_license_data():
        cmd = "steamcmd +login {} +licenses_print +quit".format(
            steam_login).split()
        proc = Popen(cmd, stdout=PIPE)
        content = [i.decode() for i in proc.stdout]
        index = [i for i, line in enumerate(content) if "License" in line][1:]

        return [{'package': int(findall(r'(\d+)', content[i])[0]),
                 'date': datetime.strptime(findall(
                     r'.* : (.+?) in .*', content[i+1])[0],
                     '%a %b %d %H:%M:%S %Y'),
                 'location': findall(r'"(.*?)"', content[i+1])[0],
                 'license': findall(r'.*\, (.*)', content[i+1])[0],
                 'apps': findall(r'(\d+)', content[i+2])[:-1]}
                for i in index]

    print("Reading games data...", end='\r')
    steam_data = read_steam_data()
    print("Reading price data...", end='\r')
    price_data = read_price_data('prices.csv')
    print("Reading license data...", end='\r')
    license_data = read_license_data()

    priced_games = merge_dict_lists(steam_data, price_data, 'appid')

    for g in priced_games:
        for l in license_data:
            if str(g['appid']) in l['apps']:
                g['package'] = l['package']
                g['date'] = l['date'].strftime('%d/%m/%Y %H:%M:%S')
                g['location'] = l['location']
                g['license'] = l['license']
                break
        if 'achiev' not in g.keys():
            g['achiev'] = ""

    return sorted(priced_games, key=lambda k: k['appid'])


def show_icon(game):
    if "img_icon_url" in game.keys():
        return ("=IMAGE(\"http://media.steampowered.com/"
                "steamcommunity/public/images/"
                "apps/{}/{}.jpg\"; 1)").format(game['appid'],
                                               game['img_icon_url'])
    return ""


def price_paid(game):
    return game['price_paid']


def time_played(game):
    if "playtime_forever" in game.keys():
        return game['playtime_forever'] / 60
    return "0"


def price_per_hour(game):
    spent = time_played(game)
    if not spent:
        return 0
    if float(spent) < 1:
        return spent
    return price_paid(game) / spent


def discount_info(game):
    if not game['orig_price']:
        return 0
    return 1 - (game['price_paid'] / game['orig_price'])


private_data = json.load(open('config.json'))
api_key = private_data['api_key']
steamid = private_data['steamid']
steam_login = private_data['steam_login']

scope = ['https://spreadsheets.google.com/feeds']
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    private_data['json_keyfile_path'], scope)

gc = login(credentials)
game_list = prep_game_list()

worksheet = gc.open_by_key(private_data['spreadsheet_key']).sheet1
index, length = 2, len(game_list)
worksheet.resize(length + (index - 1))
values_list = []

for game in game_list:
    values_list += [show_icon(game), game['appid'], game['name'],
                    price_paid(game), time_played(game), price_per_hour(game),
                    game['achiev'], discount_info(game),
                    game['package'], game['date'], game['location'],
                    game['license']]

print("Uploading to Google Drive...", end='\r')
cell_list = worksheet.range('A{}:L{}'.format(index, length + (index - 1)))

for cell, value in zip(cell_list, values_list):
    cell.value = value
worksheet.update_cells(cell_list)
