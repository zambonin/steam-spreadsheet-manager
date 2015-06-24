#!/usr/bin/python3

import datetime
import gspread
import json
import steam

from oauth2client.service_account import ServiceAccountCredentials

before = datetime.datetime.now()

private_data = json.load(open('config.json'))

scope = ['https://spreadsheets.google.com/feeds']

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    private_data['json_keyfile_path'], scope)

gc = gspread.authorize(credentials)

worksheet = gc.open_by_key(private_data['spreadsheet_key']).sheet1


def show_icon(game):
    return "=IMAGE(\""+steam.icon(game)+"\"; 1)"


def steamdb_app_link(game):
    appid = steam.appid(game)
    return "=HYPERLINK(\"steamdb.info/app/"+str(appid)+"\";"+str(appid)+")"


def steamdb_sub_link(game):
    subid = steam.subid(game)
    return "=HYPERLINK(\"steamdb.info/sub/"+str(subid)+"\";"+str(subid)+")"

games = steam.list_games()
index = 3
num_rows = len(games) + (index - 1)
worksheet.resize(num_rows)

cell_list = worksheet.range('A%s:I%s' % (index - 1, num_rows))
for game, i in zip(games, range(1, len(games) + 1)):
    print("Updating row #%s, time elapsed: %s" % (str(i + 2),
          str(datetime.datetime.now() - before)), end='\r')
    row_cells = cell_list[9*i:18*i]
    values_list = [show_icon(game), steamdb_app_link(game),
                   steamdb_sub_link(game), steam.name(steam.appid(game)),
                   steam.price(game), steam.time(game), steam.pph(game),
                   steam.achiev(game), steam.discount(game)]
    for cell, value in zip(row_cells, values_list):
        cell.value = value
worksheet.update_cells(cell_list)

after = str(datetime.datetime.now() - before)
print("Time spent on populating the spreadsheet: %s" % after)
