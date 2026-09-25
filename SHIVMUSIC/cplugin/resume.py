from ftmgram import filters, Client
from ftmgram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup

from SHIVMUSIC import app
from SHIVMUSIC.core.call import ANJALI
from SHIVMUSIC.utils.inline import close_markup
from config import BANNED_USERS
# Hum Database functions import kar rahe hain taaki state save rahe
from SHIVMUSIC.utils.database import is_music_playing, music_on

# ✅ IMPORT NEW ADMIN CHECKER (For Clone Support)
from SHIVMUSIC.cplugin.utils.decorators.admins import AdminRightsCheck

@Client.on_message(
    filters.command(["resume", "cresume"]) & filters.group & ~BANNED_USERS
)
@AdminRightsCheck # <-- Ab ye Clone Owner/Sudo ko allow karega
async def resume_com(cli, message: Message, _, chat_id):
    # Check karega ki kya music already chal raha hai?
    if await is_music_playing(chat_id):
        return await message.reply_text(_["admin_3"])
    
    await ANJALI.resume_stream(chat_id)
    # Mark it on only after the voice-chat resume succeeds.
    await music_on(chat_id)
    
    buttons_resume = [
        [
            InlineKeyboardButton(text="sᴋɪᴘ", callback_data=f"ADMIN Skip|{chat_id}"),
            InlineKeyboardButton(text="sᴛᴏᴘ", callback_data=f"ADMIN Stop|{chat_id}"),
        ],
        [
            InlineKeyboardButton(
                text="ᴘᴀᴜsᴇ",
                callback_data=f"ADMIN Pause|{chat_id}",
            ),
        ],
    ]
    await message.reply_text(
        _["admin_4"].format(message.from_user.mention),
        reply_markup=InlineKeyboardMarkup(buttons_resume),
    )