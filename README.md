## steam-spreadsheet-manager

Detailed information about a Steam library using Google Sheets' environment.

Dependencies can be installed with `pip install -r requirements.txt`.

Needed files:
* Setup your OAuth2 as explained
[here](http://gspread.readthedocs.org/en/latest/oauth2.html).
* `config.json`
  - `spreadsheet_key` takes the unintelligible Google Sheets key
  - `api_key` is your Steam API key
  - `steamid` is your Steam64 ID
  - `json_keyfile_path` is your `oauth-...-.json` file path
* result of `GET api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key=YOUR_API_KEY&steamid=YOUR_STEAMID`
as `YOUR_STEAMID.json`
* `prices.csv` (`appid, price` - price you paid for each game)
* `packages.csv` (`appid, subid` - Steam package where each app is located)
* `licenses.txt` if you want to run `licenses.py` (it's the output from
`licenses_print` on Steam console - doesn't actually do anything yet)

Usage:
* `python steam.py --plot` draws a bubble chart where all the named bubbles are
games with price per hour index over 1. Vertical axis is price, horizontal is
time played. Coloring goes from red (worst) to blue (best).
* `python steam.py --update` pulls Steam store data for each game and stores it
under `./temp`
* `python spreadsheet.py` updates your spreadsheet

<sub><sup><sub><sup>I guess I lied.</sup></sub></sup></sub>
