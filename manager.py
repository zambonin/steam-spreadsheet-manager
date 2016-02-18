#!/usr/bin/env python

import json

from datetime import datetime
from gspread import authorize
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

    def show_icon(game):
        if "img_icon_url" in game.keys():
            return ("=IMAGE(\"http://media.steampowered.com/"
                    "steamcommunity/public/images/"
                    "apps/{}/{}.jpg\"; 1)").format(game['appid'],
                                                   game['img_icon_url'])
        return ""

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
        return game['paid'] / spent

    def discount_info(game):
        if not game['orig']:
            return 0
        return 1 - (game['paid'] / game['orig'])

    def read_steam_data():
        url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        master = rget(url, params={"key": api_key, "steamid": steamid,
                      "include_played_free_games": 1, "include_appinfo": 1}
                      ).json()['response']['games']
        appids = [i['appid'] for i in master]

        urls = [("http://api.steampowered.com/ISteamUserStats/"
                "GetPlayerAchievements/v0001/?{}").format(urlencode({
                    "key": api_key,  "steamid": steamid,
                    "appid": game})) for game in appids]

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
                 'apps': findall(r'(\d+)', content[i+2])[:-1]} for i in index]

    def match_licenses(games, licenses):
        for g in games:
            for l in licenses:
                if str(g['appid']) in l['apps']:
                    g['package'] = l['package']
                    g['date'] = l['date'].strftime('%d/%m/%Y %H:%M:%S')
                    g['location'] = l['location']
                    g['license'] = l['license']
                    break
            if 'achiev' not in g.keys():
                g['achiev'] = ""

        values = [[show_icon(game), game['appid'], game['name'],
                  game['paid'], time_played(game), price_per_hour(game),
                  game['achiev'], discount_info(game), game['package'],
                  game['date'], game['location'], game['license']]
                  for game in sorted(games, key=lambda k: k['appid'])]

        return [val for sublist in values for val in sublist]

    return match_licenses(
        merge_dict_lists(read_steam_data(), json.load(open('prices.json')),
                         'appid'),
        read_license_data())


def upload_ss(game_list):
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        private_data['json_keyfile_path'], scope)

    gc = authorize(credentials)

    worksheet = gc.open_by_key(private_data['spreadsheet_key']).sheet1
    index, length = 2, int(len(game_list) / (ord('L') - ord('@')))
    worksheet.resize(length + (index - 1))

    cell_list = worksheet.range('A{}:L{}'.format(index, length + (index - 1)))

    for cell, value in zip(cell_list, game_list):
        cell.value = value
    worksheet.update_cells(cell_list)


if __name__ == "__main__":
    private_data = json.load(open('config.json'))
    api_key = private_data['api_key']
    steamid = private_data['steamid']
    steam_login = private_data['steam_login']

    upload_ss(prep_game_list())
