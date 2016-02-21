#!/usr/bin/env python

from datetime import datetime
from gspread import authorize
from json import load
from multiprocessing.dummy import Pool
from oauth2client.service_account import ServiceAccountCredentials
from re import findall
from requests import get as rget
from subprocess import Popen, PIPE


def prep_game_list(api_key, steamid, login):
    def merge_dict_lists(list1, list2, key):
        merged = {}
        for item in list1 + list2:
            if item[key] in merged:
                merged[item[key]].update(item)
            else:
                merged[item[key]] = item
        return [value for (_, value) in merged.items()]

    def show_icon(game):
        return ("=IMAGE(\"http://media.steampowered.com/steamcommunity/"
                "public/images/apps/{}/{}.jpg\"; 1)"
                ).format(game['appid'], game['img_icon_url'])

    def price_per_hour(game):
        return (game['paid'] / game['time']) if game['time'] else 0

    def discount_info(game):
        return (1 - (game['paid'] / game['orig'])) if game['orig'] else 0

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
                 'achv': sum([a['achieved'] for a in
                             i['achievements']]) / len(i['achievements'])
                 } for i in achiev_data]

    def read_steam_data():
        url = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        master = rget(url, params={"key": api_key, "steamid": steamid,
                      "include_played_free_games": 1, "include_appinfo": 1}
                      ).json()['response']['games']

        for i in master:
            i['time'] = i.pop('playtime_forever') / 60
            i['achv'] = ""

        return merge_dict_lists(
            master, read_achiev_data([i['appid'] for i in master]), 'name')

    def read_license_data():
        cmd = "steamcmd +login {} +licenses_print +quit".format(login).split()
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

        values = [[show_icon(game), game['appid'], game['name'], game['paid'],
                  game['time'], price_per_hour(game), game['achv'],
                  discount_info(game), game['package'], game['date'],
                  game['location'], game['license']]
                  for game in sorted(games, key=lambda k: k['appid'])]

        return [val for sublist in values for val in sublist]

    return match_licenses(merge_dict_lists(
        read_steam_data(), load(open('prices.json')), 'appid'),
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
    private_data = load(open('config.json'))
    upload_ss(prep_game_list(private_data['api_key'], private_data['steamid'],
                             private_data['steam_login']))
