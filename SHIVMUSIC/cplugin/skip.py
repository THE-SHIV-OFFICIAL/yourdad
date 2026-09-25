import asyncio
from ftmgram import filters, Client
from ftmgram.types import Message
from ftmgram.enums import ChatMemberStatus

import config
from SHIVMUSIC import app
from SHIVMUSIC.core.call import ANJALI
from SHIVMUSIC.misc import db

# ✅ Imports Updated
from SHIVMUSIC.utils.database import get_loop
from SHIVMUSIC.cplugin.utils.decorators.admins import AdminRightsCheck
from SHIVMUSIC.utils.inline import close_markup
from SHIVMUSIC.utils.stream.autoclear import auto_clean
from config import BANNED_USERS

# 🟢 THE FIX 1: @app.on_message ko @Client.on_message se replace kiya
# Isse Main Bot aur Clone Bot DONO is command ko sunenge!
@Client.on_message(
    filters.command(["skip", "cskip", "next", "cnext"], prefixes=["/", "!", "%", ",", ".", "@", "#"])
    & filters.group 
    & ~BANNED_USERS
)
@AdminRightsCheck
async def skip_comm(cli: Client, message: Message, _, chat_id):
    
    # 🟢 THE FIX 2: BULLETPROOF ADMIN CHECK
    # Agar decorator fail ho jaye, toh yeh manual check kisi bhi aam user ko rok dega.
    user_id = message.from_user.id
    if user_id not in config.SUDOERS:
        try:
            member = await cli.get_chat_member(chat_id, user_id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await message.reply_text("❌ **You don't have permission to use this command. Only Admins can skip.**")
        except Exception:
            return await message.reply_text("❌ **You don't have permission to use this command. Only Admins can skip.**")

    # 1. Queue check
    check = db.get(chat_id)
    if not check:
        return await message.reply_text(_["queue_2"])
    
    # 2. Loop check (Agar loop on hai, toh skip allow nahi hoga)
    loop = await get_loop(chat_id)
    if loop != 0:
        return await message.reply_text(_["admin_8"])

    # 3. Multi-skip logic (e.g., /skip 3)
    skip_count = 1
    if len(message.command) > 1:
        state = message.text.split(None, 1)[1].strip()
        if state.isnumeric():
            state = int(state)
            if 1 <= state <= len(check):
                skip_count = state
            else:
                return await message.reply_text(_["admin_11"].format(len(check)))
        else:
            return await message.reply_text(_["admin_11"].format(len(check)-1))

    # 4. Actual Skip Logic
    try:
        # Pehle (skip_count - 1) songs ko queue se nikal kar clean up karo
        if skip_count > 1:
            for x in range(skip_count - 1):
                try:
                    popped = check.pop(0)
                    if popped:
                        await auto_clean(popped)
                except:
                    pass
        
        # Sahi PyTgCalls client (assistant) get karo
        clients = await ANJALI.get_active_clients(chat_id)
        pytgcalls_client = clients[0] if clients else ANJALI.one
            
        # change_stream call karo. 
        # Yeh automatic bacha hua gaana pop karega, next play karega, aur UI stream_card bhej dega!
        await ANJALI.change_stream(pytgcalls_client, chat_id)
        
        # Skip confirmation
        await message.reply_text(f"➻ sᴛʀᴇᴀᴍ sᴋɪᴩᴩᴇᴅ 🎄\n└ʙʏ : {message.from_user.mention}")
        
    except Exception as e:
        # Agar error aaya toh gracefully handle karo
        try:
            await message.reply_text(
                text=_["admin_6"].format(message.from_user.mention, message.chat.title),
                reply_markup=close_markup(_)
            )
            await ANJALI.stop_stream(chat_id)
        except:
            pass
