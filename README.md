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
  - `steam_login` is your Steam login name (not the public one!)
  - `json_keyfile_path` is your `oauth-...-.json` file path
* `prices.json` (`appid, name, orig, paid`)
  - `appid` - game's appid
  - `name` - game's name
  - `orig` - game's store price
  - `paid` - price you paid for it

Usage: `python manager.py`

