# DNDBot
If your character name includes whitespace, always surround it with `"double quotes"`

# Using the bot to talk in character
## Create a character
Create a character by typing `+char add [name] [displayname] [picture_url]`  
Create an npc by typing `+char add [name] [displayname] [picture_url] npc` 
## Select a character/make a character active
Select a character/make it active with `+char [name]` 
## Writing in character
Write a message with your active character by writing `++ [your_message]`  
Write a message with another character by writing `++ [name] [your_message]` 
## Manage your characters
List all your created character with `+char list`  
Show a character\'s configuration with `+char info [name]` (name can be omitted if you have an active char)  
Edit a character with `+char edit [name] [attribute] [new_value]`  
Delete a character by typing `+char delete [name] (careful)` 

## How to run the bot
* Create a discord application/bot on the https://discord.com/developers site
* Pull this repository and `cd` to it
* set up the config file (see below)
### Run the bot with docker
* To start the bot `docker-compose up -d` 
* To stop the bot `docker-compose down`

### Run the bot without docker
* If you want to use a venv set it up and activate it now 
* Install `discord.py` and `sqlalchemy` (`pip install -U -r requirements.txt`)
* To start the bot: `cd src` -> `python3 -u bot.py`
* To stop the bot: `Ctrl+C` or use the bot admin command `+stop`


### Set up the Config File
* copy the `state/config.json.sample` to `state/config.json` and enter your settings
* `bot_key` is your bot token of your discord application
  + example: `"bot_key": "abcd1234",`
* `admins` is a list of IDs of discord users that can use the admin commands (on the server and in DMs)
  + example: `"admins": [123456789, 987654321],`
* `admin_roles` is a list of IDs of discord roles that can use the admin commands (on the server only)
  + example: `"admin_roles": [123456789, 987654321],`
* `ranks` is a list of IDs of discord roles that represent the different guild ranks (colors) 
  + **Important: This list has to be ordered from "highest" rank (first) to "lowest" rank (last)**
  + example: `"ranks": [123, 456, 789, 258, 964],`
* `mainguild` is the id of the discord server/guild where the bot will be run in
  + example: `"mainguild": 123456789,`
