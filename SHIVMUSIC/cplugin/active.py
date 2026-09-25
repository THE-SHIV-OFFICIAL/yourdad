from ftmgram import filters, Client
from ftmgram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from SHIVMUSIC.utils.database import (
    get_active_chats,
    get_active_video_chats,
)
from SHIVMUSIC.utils.database.clonedb import get_served_chats_clone, clonebotdb

@Client.on_message(filters.command(["ac", "activevc", "activevoice"]))
async def start(client: Client, message: Message):
    
    bot_id = client.me.id
    user_id = message.from_user.id
    
    # Fetch Owner from Database
    clone_data = await clonebotdb.find_one({"bot_id": bot_id})
    
    if not clone_data:
        return 
        
    owner_id = clone_data.get("user_id")

    # STRICT OWNER CHECK
    if user_id != owner_id:
        return await message.reply_text("❌ **Only the Bot Owner can view these stats.**")

    waiting_msg = await message.reply_text("🔄 **Checking active groups...**")

    # DATA FETCHING
    global_audio = await get_active_chats()
    global_video = await get_active_video_chats()

    # Fetch Served Chats for this specific bot
    try:
        clone_served_chats = await get_served_chats_clone(bot_id)
        my_chat_ids = [int(chat["chat_id"]) for chat in clone_served_chats]
    except Exception:
        my_chat_ids = []

    # FILTERING (FIXED: Added int() casting and try-except for safety)
    my_audio_count = 0
    if global_audio:
        for chat_id in global_audio:
            try:
                if int(chat_id) in my_chat_ids:
                    my_audio_count += 1
            except Exception:
                continue

    my_video_count = 0
    if global_video:
        for chat_id in global_video:
            try:
                if int(chat_id) in my_chat_ids:
                    my_video_count += 1
            except Exception:
                continue

    # RESULT
    text = (
        f"📊 **Bot Activity Status**\n\n"
        f"👤 **Owner:** {message.from_user.mention}\n"
        f"🤖 **Bot:** @{client.me.username}\n\n"
        f"🏢 **Total Groups:** `{len(my_chat_ids)}`\n"
        f"🎧 **Active Audio:** `{my_audio_count}`\n"
        f"📹 **Active Video:** `{my_video_count}`\n"
    )
    
    await waiting_msg.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✯ Close ✯", callback_data="close")]]
        ),
    )
