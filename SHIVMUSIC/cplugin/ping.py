import time
import random
import psutil
from ftmgram import Client, filters
from ftmgram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

# Config Imports
from config import SUPPORT_CHAT, PING_IMG_URL, OWNER_ID, BANNED_USERS
from SHIVMUSIC import app
from SHIVMUSIC.misc import _boot_
from SHIVMUSIC.utils import get_readable_time
from SHIVMUSIC.utils.rich_helper import build_rich_stats

# Database Imports
from SHIVMUSIC.utils.database.clonedb import (
    get_owner_id_from_db,
    get_cloned_support_chat,
)
from SHIVMUSIC.utils.database import clonebotdb

# --- HELPER FUNCTIONS ---

def get_random_ping_img():
    if PING_IMG_URL:
        if isinstance(PING_IMG_URL, list):
            return random.choice(PING_IMG_URL)
        return PING_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"

async def get_ping_image(bot_id: int):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("ping_image")

async def get_ping_video(bot_id: int):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("ping_video")

# ✅ New Helper to Add Random Content
async def add_ping_content(bot_id, key, value):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    current = d.get(key)
    
    if current:
        if value in current:
            return False # Duplicate check
        final_value = f"{current}|||{value}"
    else:
        final_value = value
        
    await clonebotdb.update_one({"bot_id": bot_id}, {"$set": {key: final_value}}, upsert=True)
    return True

# =====================================================================
# /ping COMMAND
# =====================================================================

@Client.on_message(filters.command("ping") & ~BANNED_USERS)
async def ping_clone(client: Client, message: Message):
    bot = await client.get_me()
    bot_id = bot.id

    # Fetch Support Chat
    try:
        C_BOT_SUPPORT_CHAT = await get_cloned_support_chat(bot_id)
        if C_BOT_SUPPORT_CHAT:
            C_SUPPORT_CHAT = f"https://t.me/{C_BOT_SUPPORT_CHAT}" if "t.me" not in C_BOT_SUPPORT_CHAT else C_BOT_SUPPORT_CHAT
        else:
            C_SUPPORT_CHAT = SUPPORT_CHAT
    except:
        C_SUPPORT_CHAT = SUPPORT_CHAT

    # Fetch Custom Media (Raw Data)
    raw_ping_video = await get_ping_video(bot_id)
    raw_ping_img = await get_ping_image(bot_id)
    
    # ✅ RANDOM SELECTION LOGIC
    ping_video = None
    if raw_ping_video:
        if "|||" in raw_ping_video:
            ping_video = random.choice(raw_ping_video.split("|||"))
        else:
            ping_video = raw_ping_video

    ping_img = None
    if raw_ping_img:
        if "|||" in raw_ping_img:
            ping_img = random.choice(raw_ping_img.split("|||"))
        else:
            ping_img = raw_ping_img
    
    start = time.perf_counter()
    caption_text = f"{bot.mention} is pinging..."
    
    hmm = None
    
    # 1. PRIORITY: VIDEO
    if ping_video:
        try:
            hmm = await message.reply_video(video=ping_video, caption=caption_text, has_spoiler=True)
        except Exception:
            pass 

    # 2. PRIORITY: CUSTOM IMAGE
    if not hmm and ping_img:
        try:
            hmm = await message.reply_photo(photo=ping_img, caption=caption_text, has_spoiler=True)
        except Exception:
            pass

    # 3. PRIORITY: DEFAULT RANDOM IMAGE
    if not hmm:
        try:
            hmm = await message.reply_photo(photo=get_random_ping_img(), caption=caption_text, has_spoiler=True)
        except Exception:
            # Fallback to Text
            hmm = await message.reply_text(caption_text)

    # 🚀 FIXED: Non-blocking stats calculation
    upt = int(time.time() - _boot_)
    cpu = psutil.cpu_percent(interval=None) # Interval 'None' ensures it doesn't freeze the bot
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    resp = (time.perf_counter() - start) * 1000
    uptime = get_readable_time(upt)

    rich_msg = build_rich_stats(
        f"Pong: {resp:.2f} ms",
        {
            # Rich table cells intentionally contain plain text only. The
            # Bot.mention property is an HTML anchor and used to print its
            # literal <a href=...> markup inside the screenshot's Value cell.
            "Bot": f"@{bot.username}" if bot.username else f"ID {bot.id}",
            "Uptime": uptime,
            "RAM": f"{mem}%",
            "CPU": f"{cpu}%",
            "Disk": f"{disk}%",
        },
    )

    markup = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "🎧 Support",
                url=C_SUPPORT_CHAT,
                icon_custom_emoji_id=5462921117423384478,
            )
        ]]
    )

    try:
        await hmm.delete()
        await client.send_rich_message(
            chat_id=message.chat.id,
            rich_message=rich_msg,
            reply_markup=markup,
            reply_to_message_id=message.id,
        )
    except Exception:
        pass


# =====================================================================
# SETTINGS COMMANDS (Now Supports Adding Multiple)
# =====================================================================

@Client.on_message(filters.command(["setpingimg", "addpingimg"]) & ~BANNED_USERS)
async def set_ping_image(client: Client, message: Message):
    bot = await client.get_me()
    bot_id = bot.id
    
    # 🚀 FIXED: Proper Exception Handling for Async Function
    try:
        owner_id = await get_owner_id_from_db(bot_id)
    except Exception:
        owner_id = OWNER_ID
        
    if message.from_user.id not in [OWNER_ID, owner_id]:
        return await message.reply_text("🚫 Only the Bot Owner can use this command.")

    # 1. Reply to Photo
    if message.reply_to_message and message.reply_to_message.photo:
        file_id = message.reply_to_message.photo.file_id
        await add_ping_content(bot_id, "ping_image", file_id)
        return await message.reply_text("✅ Photo added to Random Ping List!")

    # 2. URL Argument
    if len(message.command) == 2:
        url = message.command[1].strip()
        await add_ping_content(bot_id, "ping_image", url)
        return await message.reply_text("✅ Image URL added to Random Ping List!")

    return await message.reply_text("❗ Reply to a photo or use /addpingimg [URL]")


@Client.on_message(filters.command(["delpingimg", "resetpingimg"]) & ~BANNED_USERS)
async def del_ping_image(client: Client, message: Message):
    bot = await client.get_me()
    bot_id = bot.id

    try:
        owner_id = await get_owner_id_from_db(bot_id)
    except Exception:
        owner_id = OWNER_ID
        
    if message.from_user.id not in [OWNER_ID, owner_id]:
        return await message.reply_text("🚫 Only the Bot Owner can use this command.")

    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"ping_image": ""}})
    return await message.reply_text("🗑 All custom ping images removed! (Reset to Default)")


@Client.on_message(filters.command(["setpingvideo", "addpingvideo"]) & ~BANNED_USERS)
async def set_ping_video(client: Client, message: Message):
    bot = await client.get_me()
    bot_id = bot.id
    
    try:
        owner_id = await get_owner_id_from_db(bot_id)
    except Exception:
        owner_id = OWNER_ID
        
    if message.from_user.id not in [OWNER_ID, owner_id]:
        return await message.reply_text("🚫 Only the Bot Owner can use this command.")

    # 1. Reply to Video
    if message.reply_to_message and message.reply_to_message.video:
        file_id = message.reply_to_message.video.file_id
        await add_ping_content(bot_id, "ping_video", file_id)
        return await message.reply_text("✅ Video added to Random Ping List!")

    # 2. Reply to GIF
    if message.reply_to_message and message.reply_to_message.animation:
        file_id = message.reply_to_message.animation.file_id
        await add_ping_content(bot_id, "ping_video", file_id)
        return await message.reply_text("✅ GIF added to Random Ping List!")

    # 3. URL Argument
    if len(message.command) == 2:
        url = message.command[1].strip()
        await add_ping_content(bot_id, "ping_video", url)
        return await message.reply_text("✅ Video URL added to Random Ping List!")

    return await message.reply_text("❗ Reply to a video/GIF or use /addpingvideo [URL]")


@Client.on_message(filters.command(["delpingvideo", "resetpingvideo"]) & ~BANNED_USERS)
async def del_ping_video(client: Client, message: Message):
    bot = await client.get_me()
    bot_id = bot.id

    try:
        owner_id = await get_owner_id_from_db(bot_id)
    except Exception:
        owner_id = OWNER_ID
        
    if message.from_user.id not in [OWNER_ID, owner_id]:
        return await message.reply_text("🚫 Only the Bot Owner can use this command.")

    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"ping_video": ""}})
    return await message.reply_text("🗑 All custom ping videos removed! (Reset to Default)")
