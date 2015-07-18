#!/usr/bin/python3

import glob
import gspread
import json
import locale
import re

from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials


def show_icon(game):
    if "img_icon_url" in list(game.keys()):
        return "=IMAGE(\"http://media.steampowered.com/" + \
            "steamcommunity/public/images/apps/" + \
            str(game['appid']) + "/" + game['img_icon_url'] + \
            ".jpg"+"\"; 1)"
    return ""


def app_link(game):
    return "=HYPERLINK(\"steamdb.info/app/" + \
            str(game['appid']) + "\";" + str(game['appid']) + ")"


def price(game):
    return locale.str(game['price_paid'])


def time(game):
    if "playtime_forever" in list(game.keys()):
        return locale.str(game['playtime_forever'] / 60)
    return "0"


def pph(game):
    spent = locale.atof(time(game))
    paid = locale.atof(price(game))
    if not spent:
        return 0
    if spent < 1:
        return locale.str(spent)
    return locale.str(paid / spent)


def discount(game):
    if not game['orig_price']:
        return 1
    fluct = abs((game['price_paid'] * 100 / game['orig_price']) - 1)
    return locale.str(fluct)


def sub_link(game):
    return "=HYPERLINK(\"steamdb.info/sub/" + \
            str(game['package']) + "\";" + str(game['package']) + ")"


def achiev(game):
    if type(game['achiev']) == str:
        return ""
    return locale.str(game['achiev'])


def read_games():
    def numericalSort(value):
        parts = re.compile(r'(\d+)').split(value)
        parts[1::2] = map(int, parts[1::2])
        return parts

    list_games = []
    for file in sorted(glob.glob("temp/*.in"), key=numericalSort):
        with open(file) as game:
            list_games.append(json.loads(game.read()))

    return list_games

before = datetime.now()
locale.setlocale(locale.LC_ALL, '')

print("Connecting to Google Drive...", end='\r')

private_data = json.load(open('config.json'))

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    private_data['json_keyfile_path'], scope)

gc = gspread.authorize(credentials)

worksheet = gc.open_by_key(private_data['spreadsheet_key']).sheet1

games = read_games()

index = 2
worksheet.resize(len(games) + (index - 1))

for game, i in zip(games, range(index, len(games) + index)):
    cell_list = worksheet.range('A%s:L%s' % (i, i))
    print("Updating row #%s, time elapsed: %s" %
          (str(i), str(datetime.now() - before)), end='\r')
    values_list = [
                    show_icon(game),
                    app_link(game),
                    game['name'],
                    price(game),
                    time(game),
                    pph(game),
                    achiev(game),
                    discount(game),
                    sub_link(game),
                    game['date'],
                    game['location'],
                    game['license']
                ]
    for cell, value in zip(cell_list, values_list):
        cell.value = value
    worksheet.update_cells(cell_list)

after = str(datetime.now() - before)

print("Time spent on populating the spreadsheet: %s" % after)
