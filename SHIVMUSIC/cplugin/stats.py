import platform
import random
from sys import version as pyver

import psutil
from ftmgram import __version__ as pyrover
from ftmgram import filters, Client
from ftmgram.errors import MessageIdInvalid
from ftmgram.types import InputMediaPhoto, Message
from pytgcalls.__version__ import __version__ as pytgver

import config
from SHIVMUSIC import app
from SHIVMUSIC.core.userbot import assistants
from SHIVMUSIC.misc import SUDOERS, mongodb
from SHIVMUSIC.plugins import ALL_MODULES
from SHIVMUSIC.utils.database import (
    get_served_chats_clone,
    get_served_users_clone,
    get_sudoers,
)
from SHIVMUSIC.utils.decorators.language import language, languageCB
from SHIVMUSIC.utils.rich_helper import build_rich_stats
from SHIVMUSIC.utils.inline.stats import back_stats_buttons, stats_buttons
from config import BANNED_USERS


# ✅ Helper to get Random Stats Image
def get_random_stats_img():
    if config.STATS_IMG_URL:
        if isinstance(config.STATS_IMG_URL, list):
            return random.choice(config.STATS_IMG_URL)
        return config.STATS_IMG_URL
    return "https://files.catbox.moe/6r97s4.jpg"


@Client.on_message(filters.command(["stats", "gstats"]) & ~BANNED_USERS)
@language
async def stats_global(client: Client, message: Message, _):
    a = await client.get_me()
    upl = stats_buttons(_, True if message.from_user.id in SUDOERS else False)
    
    await message.reply_photo(
        photo=get_random_stats_img(),
        caption=_["gstats_2"].format(a.mention),
        reply_markup=upl,
    )


@Client.on_callback_query(filters.regex("stats_back") & ~BANNED_USERS)
@languageCB
async def home_stats(client, CallbackQuery, _):
    a = await client.get_me()
    upl = stats_buttons(_, True if CallbackQuery.from_user.id in SUDOERS else False)
    
    await CallbackQuery.edit_message_text(
        text=_["gstats_2"].format(a.mention),
        reply_markup=upl,
    )


@Client.on_callback_query(filters.regex("TopOverall") & ~BANNED_USERS)
@languageCB
async def overall_stats(client, CallbackQuery, _):
    a = await client.get_me()
    bot_id = a.id
    try:
        await CallbackQuery.answer()
    except:
        pass
    upl = back_stats_buttons(_)
    
    await CallbackQuery.edit_message_text(_["gstats_1"].format(a.mention))
    
    served_chats = len(await get_served_chats_clone(bot_id))
    served_users = len(await get_served_users_clone(bot_id))
    
    rich_msg = build_rich_stats(
        f"Stats for @{a.username}",
        {
            "Assistants": len(assistants),
            "Blocked": len(BANNED_USERS),
            "Chats": served_chats,
            "Users": served_users,
            "Modules": len(ALL_MODULES),
            "Sudo Users": len(SUDOERS),
            "Auto Leave": config.AUTO_LEAVING_ASSISTANT,
            "Duration Limit": f"{config.DURATION_LIMIT_MIN} min",
        },
    )
    await client.edit_message_text(
        chat_id=CallbackQuery.message.chat.id,
        message_id=CallbackQuery.message.id,
        rich_message=rich_msg,
        reply_markup=upl,
    )


@Client.on_callback_query(filters.regex("bot_stats_sudo"))
@languageCB
async def bot_stats(client, CallbackQuery, _):
    a = await client.get_me()
    bot_id = a.id
    if CallbackQuery.from_user.id not in SUDOERS:
        return await CallbackQuery.answer(_["gstats_4"], show_alert=True)
    upl = back_stats_buttons(_)
    try:
        await CallbackQuery.answer()
    except:
        pass
        
    await CallbackQuery.edit_message_text(_["gstats_1"].format(a.mention))
    
    p_core = psutil.cpu_count(logical=False)
    t_core = psutil.cpu_count(logical=True)
    ram = str(round(psutil.virtual_memory().total / (1024.0**3))) + " GB"
    try:
        cpu_freq = psutil.cpu_freq().current
        if cpu_freq >= 1000:
            cpu_freq = f"{round(cpu_freq / 1000, 2)}GHz"
        else:
            cpu_freq = f"{round(cpu_freq, 2)}MHz"
    except:
        cpu_freq = "Failed to fetch"
    
    hdd = psutil.disk_usage("/")
    total = hdd.total / (1024.0**3)
    used = hdd.used / (1024.0**3)
    free = hdd.free / (1024.0**3)
    
    served_chats = len(await get_served_chats_clone(bot_id))
    served_users = len(await get_served_users_clone(bot_id))
    
    stats_data = {
        "Modules": len(ALL_MODULES),
        "Platform": platform.system(),
        "RAM": ram,
        "Cores": f"{p_core}/{t_core}",
        "CPU": cpu_freq,
        "Python": pyver.split()[0],
        "FTMGram": pyrover,
        "Storage": f"{used:.1f}/{total:.1f} GB",
        "Free": f"{free:.1f} GB",
        "Chats": served_chats,
        "Users": served_users,
    }
    rich_msg = build_rich_stats(f"Clone Bot Stats: @{a.username}", stats_data)
    await client.edit_message_text(
        chat_id=CallbackQuery.message.chat.id,
        message_id=CallbackQuery.message.id,
        rich_message=rich_msg,
        reply_markup=upl,
    )
