# Old "pyrogram" (pulled in by pykeyboard/SafoneAPI) breaks PyTgCalls.
# Route every "pyrogram" import to ftmgram before anything else loads.
from SHIVMUSIC.core.call_compat import alias_pyrogram_to_ftmgram as _alias
_alias()
from SHIVMUSIC.core.bot import ANJALI
from SHIVMUSIC.core.dir import dirr
from SHIVMUSIC.core.git import git
from SHIVMUSIC.core.userbot import Userbot
from SHIVMUSIC.misc import dbb, heroku
from ftmgram import Client
from SafoneAPI import SafoneAPI
from .logging import LOGGER

dirr()
git()
dbb()
heroku()

app = ANJALI()
api = SafoneAPI()
userbot = Userbot()

from .platforms import *

Apple = AppleAPI()
Carbon = CarbonAPI()
SoundCloud = SoundAPI()
Spotify = SpotifyAPI()
Resso = RessoAPI()
Telegram = TeleAPI()
YouTube = YouTubeAPI()
