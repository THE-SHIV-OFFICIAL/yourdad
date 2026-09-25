import asyncio
from ftmgram import filters, Client
from ftmgram.types import Message

from SHIVMUSIC import YouTube
from SHIVMUSIC.core.call import ANJALI
from SHIVMUSIC.misc import db
from SHIVMUSIC.utils.formatters import seconds_to_min
from SHIVMUSIC.utils.inline import close_markup
from config import BANNED_USERS

# ✅ IMPORT NEW ADMIN CHECKER (For Clone Support)
from SHIVMUSIC.cplugin.utils.decorators.admins import AdminRightsCheck

@Client.on_message(
    # 🚀 FIX: Added all custom prefixes
    filters.command(["seek", "cseek", "seekback", "cseekback"], prefixes=["/", "!", "#"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck # <-- Ab ye Clone Owner/Sudo ko allow karega
async def seek_comm(cli, message: Message, _, chat_id):
    if len(message.command) == 1:
        return await message.reply_text(_["admin_20"])
        
    query = message.text.split(None, 1)[1].strip()
    if not query.isnumeric():
        return await message.reply_text(_["admin_21"])
        
    playing = db.get(chat_id)
    if not playing:
        return await message.reply_text(_["queue_2"])
        
    # 🚀 Safe get() to prevent KeyError
    duration_seconds = int(playing[0].get("seconds", 0))
    duration_played = int(playing[0].get("played", 0))
    duration_to_skip = int(query)
    duration_str = playing[0].get("dur", "0:00")
    
    if duration_seconds == 0:
        return await message.reply_text(_["admin_22"])
        
    # 🟢 THE FIX: "seekback" check karne ka sabse safe tarika
    is_backward = "back" in message.command[0].lower()
    
    # Calculate target time safely
    if is_backward:
        to_seek = duration_played - duration_to_skip
        if to_seek < 0: 
            to_seek = 0
    else:
        to_seek = duration_played + duration_to_skip
        if to_seek > duration_seconds: 
            to_seek = duration_seconds - 5
            
    # Safety limit check (Start ya end ke bahut close ho toh ignore karein)
    if abs(duration_played - to_seek) < 10:
        return await message.reply_text(
            text=_["admin_23"].format(seconds_to_min(duration_played), duration_str),
            reply_markup=close_markup(_),
        )

    mystic = await message.reply_text(_["admin_24"])
    
    # File path setup
    file_path = playing[0].get("file", "")
    if "vid_" in file_path:
        n, file_path = await YouTube.video(playing[0]["vidid"], True)
        if n == 0: 
            return await mystic.edit_text(_["admin_22"])
            
    speed_path = playing[0].get("speed_path")
    if speed_path: 
        file_path = speed_path
        
    if "index_" in file_path:
        file_path = playing[0]["vidid"]
        
    try:
        # Stream ko nayi position par seek karo
        await ANJALI.seek_stream(
            chat_id,
            file_path,
            seconds_to_min(to_seek),
            duration_str,
            playing[0].get("streamtype", "audio"),
        )
    except Exception as e:
        return await mystic.edit_text(_["admin_26"], reply_markup=close_markup(_))
        
    # 🚀 Safe DB update (Synchronized)
    db[chat_id][0]["played"] = to_seek
        
    await mystic.edit_text(
        text=_["admin_25"].format(seconds_to_min(to_seek), message.from_user.mention),
        reply_markup=close_markup(_),
    )
