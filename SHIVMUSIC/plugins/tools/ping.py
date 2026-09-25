import random 
from datetime import datetime

from ftmgram import filters
from ftmgram.types import Message

from SHIVMUSIC import app
from SHIVMUSIC.core.call import ANJALI
from SHIVMUSIC.utils import bot_sys_stats
from SHIVMUSIC.utils.decorators.language import language
from SHIVMUSIC.utils.inline import supp_markup
from SHIVMUSIC.utils.rich_helper import build_rich_stats
from config import BANNED_USERS, PING_IMG_URL


@app.on_message(
    filters.command(["ping", "alive"], prefixes=["/", "!", "#"]) 
    & ~BANNED_USERS
)
@language
async def ping_com(client, message: Message, _):
    start = datetime.now()
    
    # --- RANDOM IMAGE LOGIC ---
    if isinstance(PING_IMG_URL, list):
        response_img = random.choice(PING_IMG_URL)
    else:
        response_img = PING_IMG_URL

    response = await message.reply_text(_["ping_1"].format(app.mention))
    
    # Stats calculate kar rahe hain
    pytgping = await ANJALI.ping()
    UP, CPU, RAM, DISK = await bot_sys_stats()
    resp = (datetime.now() - start).microseconds / 1000
    
    rich_msg = build_rich_stats(
        f"Pong: {resp:.2f} ms",
        {
            "Bot": app.mention,
            "Uptime": UP,
            "RAM": RAM,
            "CPU": CPU,
            "Disk": DISK,
            "PyTgCalls": f"{pytgping} ms",
        },
    )
    await client.edit_message_text(
        chat_id=response.chat.id,
        message_id=response.id,
        rich_message=rich_msg,
        reply_markup=supp_markup(_),
    )
