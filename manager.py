#!/usr/bin/env python

from datetime import datetime
from gspread import authorize
from json import load
from multiprocessing.dummy import Pool
from oauth2client.service_account import ServiceAccountCredentials
from os import path
from re import findall
from requests import get as rget
from subprocess import Popen, PIPE


def merge_dict_lists(list1, list2, key):
    merged = {}
    for item in list1 + list2:
        if item[key] in merged:
            merged[item[key]].update(item)
        else:
            merged[item[key]] = item
    return [value for (_, value) in merged.items()]


def read_steam_data(api_key, steamid, achiev=False):
    def read_achiev_data(appids):
        urls = [("http://api.steampowered.com/ISteamUserStats/"
                 "GetPlayerAchievements/v0001/?key={}&steamid={}&appid={}"
                 ).format(api_key, steamid, game) for game in appids]

        pool = Pool(len(urls))
        results = pool.map(rget, urls)
        pool.close()
        pool.join()

        achiev_data = [i for i in [j.json()['playerstats'] for j in results]
                       if i['success'] and 'achievements' in i.keys()]

        return [{'name': i['gameName'],
                 'achv': sum(a['achieved'] for a in
                             i['achievements']) / len(i['achievements'])
                 } for i in achiev_data]

    url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    master = rget(url, params={"key": api_key, "steamid": steamid,
                  "include_played_free_games": 1, "include_appinfo": 1}
                  ).json()['response']['games']

    for i in master:
        i['time'] = i.pop('playtime_forever') / 60
        i['achv'] = ""

    if achiev:
        achiev_data = read_achiev_data(i['appid'] for i in master)
        return merge_dict_lists(master, achiev_data, 'name')
    return master


def read_license_data(login):
    cmd = "steamcmd +login {} +licenses_print +quit".format(login).split()
    content = [i.decode() for i in Popen(cmd, stdout=PIPE).stdout]
    index = [i for i, line in enumerate(content) if "License" in line][1:]

    return [{'package': int(findall(r'(\d+)', content[i])[0]),
             'date': datetime.strptime(findall(
                 r'.* : (.+?) in .*', content[i+1])[0],
                 '%a %b %d %H:%M:%S %Y'),
             'location': findall(r'"(.*?)"', content[i+1])[0],
             'license': findall(r'.*\, (.*)', content[i+1])[0],
             'apps': findall(r'(\d+)', content[i+2])[:-1]} for i in index]


def add_remaining_info(games, licenses):
    def show_icon(game):
        return ("=IMAGE(\"http://media.steampowered.com/steamcommunity/"
                "public/images/apps/{}/{}.jpg\"; 1)"
                ).format(game['appid'], game['img_icon_url'])

    def price_per_hour(game):
        return (game['paid'] / game['time']) if game['time'] else 0

    def discount_info(game):
        return (1 - (game['paid'] / game['orig'])) if game['orig'] else 0

    values = []
    for g in sorted(games, key=lambda k: k['appid']):
        for l in licenses:
            if str(g['appid']) in l['apps']:
                g['package'] = l['package']
                g['date'] = l['date'].strftime('%m/%d/%Y %H:%M:%S')
                g['location'] = l['location']
                g['license'] = l['license']
                break

        values += [show_icon(g), g['appid'], g['name'], g['paid'], g['time'],
                   price_per_hour(g), g['achv'], discount_info(g),
                   g['package'], g['date'], g['location'], g['license']]

    return values


def upload_ss(game_list, keyfile, ss_key):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        keyfile, ['https://spreadsheets.google.com/feeds'])
    gc = authorize(credentials)

    worksheet = gc.open_by_key(ss_key).sheet1
    index, length = 2, int(len(game_list) / (ord('L') - ord('A') + 1))
    worksheet.resize(length + (index - 1))

    cell_list = worksheet.range('A{}:L{}'.format(index, length + (index - 1)))

    for cell, value in zip(cell_list, game_list):
        cell.value = value
    worksheet.update_cells(cell_list)


if __name__ == "__main__":
    private_data = load(open(path.join(path.dirname(__file__), 'config.json')))

    steam_data = read_steam_data(private_data['api_key'],
                                 private_data['steamid'], True)
    prices_file = load(open(path.join(path.dirname(__file__), 'prices.json')))

    steam_with_prices = merge_dict_lists(steam_data, prices_file, 'appid')
    licenses = read_license_data(private_data['steam_login'])

    keyfile = path.join(path.dirname(__file__),
                        private_data['json_keyfile_path'])

    ss_key = private_data['spreadsheet_key']

    upload_ss(add_remaining_info(steam_with_prices, licenses), keyfile, ss_key)
