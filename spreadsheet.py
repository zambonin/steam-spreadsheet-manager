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

games = steam.read_games()

index = 3
num_rows = len(games) + (index - 1)
worksheet.resize(num_rows)

for game, i in zip(games, range(index, len(games) + index)):
    cell_list = worksheet.range('A%s:L%s' % (i, i))
    print("Updating row #%s, time elapsed: %s" %
          (str(i), str(datetime.datetime.now() - before)), end='\r')
    values_list = [
                    steam.show_icon(game),
                    steam.app_link(game),
                    game['name'],
                    steam.price(game),
                    steam.time(game),
                    steam.pph(game),
                    game['achiev'],
                    steam.discount(game),
                    steam.sub_link(game),
                    game['date'],
                    game['location'],
                    game['license']
                ]
    for cell, value in zip(cell_list, values_list):
        cell.value = value
    worksheet.update_cells(cell_list)

after = str(datetime.datetime.now() - before)
print("Time spent on populating the spreadsheet: %s" % after)
