from ftmgram import filters, Client
from ftmgram.types import Message
from ftmgram.enums import ChatMemberStatus # 🟢 Zaroori Import

import config # 🟢 Zaroori Import
from SHIVMUSIC import app
from SHIVMUSIC.utils import extract_user, int_to_alpha
from SHIVMUSIC.utils.database import (
    delete_authuser,
    get_authuser,
    get_authuser_names,
    save_authuser,
)
from SHIVMUSIC.utils.decorators import language
from SHIVMUSIC.utils.inline import close_markup
from config import BANNED_USERS, adminlist

@Client.on_message(filters.command(["auth", "cauth"], prefixes=["/", "!"]) & filters.group & ~BANNED_USERS)
@language
async def auth(client: Client, message: Message, _):
    
    # 🟢 THE FIX: BULLETPROOF ADMIN CHECK
    # Koi aam user kisi ko auth nahi kar payega
    if message.from_user.id not in config.SUDOERS:
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await message.reply_text("❌ **Sirf Admins he is command ko use kar sakte hain!**")
        except Exception:
            return await message.reply_text("❌ **Error: Admin rights verify nahi ho paye.**")

    if not message.reply_to_message:
        if len(message.command) != 2:
            return await message.reply_text(_["general_1"])
    
    user = await extract_user(message)
    
    # ✅ FIX: Added await here so it doesn't crash MongoDB
    token = await int_to_alpha(user.id)
    
    _check = await get_authuser_names(message.chat.id)
    count = len(_check)
    
    if int(count) == 25:
        return await message.reply_text(_["auth_1"])
        
    if token not in _check:
        assis = {
            "auth_user_id": user.id,
            "auth_name": user.first_name,
            "admin_id": message.from_user.id,
            "admin_name": message.from_user.first_name,
        }
        
        if message.chat.id not in adminlist:
            adminlist[message.chat.id] = []
            
        if user.id not in adminlist[message.chat.id]:
            adminlist[message.chat.id].append(user.id)
        
        await save_authuser(message.chat.id, token, assis)
        return await message.reply_text(_["auth_2"].format(user.mention))
    else:
        return await message.reply_text(_["auth_3"].format(user.mention))

@Client.on_message(filters.command(["unauth", "cunauth"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
@language
async def unauthusers(client: Client, message: Message, _):
    
    # 🟢 THE FIX: BULLETPROOF ADMIN CHECK
    if message.from_user.id not in config.SUDOERS:
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                return await message.reply_text("❌ **Sirf Admins he is command ko use kar sakte hain!**")
        except Exception:
            return await message.reply_text("❌ **Error: Admin rights verify nahi ho paye.**")

    if not message.reply_to_message:
        if len(message.command) != 2:
            return await message.reply_text(_["general_1"])
    
    user = await extract_user(message)
    
    # ✅ FIX: Added await here so it doesn't crash MongoDB
    token = await int_to_alpha(user.id)
    
    deleted = await delete_authuser(message.chat.id, token)
    
    if message.chat.id in adminlist:
        if user.id in adminlist[message.chat.id]:
            adminlist[message.chat.id].remove(user.id)
            
    if deleted:
        return await message.reply_text(_["auth_4"].format(user.mention))
    else:
        return await message.reply_text(_["auth_5"].format(user.mention))

@Client.on_message(filters.command(["authlist", "authusers", "cauthlist"], prefixes=["/", "!", "%", ",", ".", "@", "#"]) & filters.group & ~BANNED_USERS)
@language
async def authusers(client: Client, message: Message, _):
    auth_names = await get_authuser_names(message.chat.id)
    
    if not auth_names:
        return await message.reply_text(_["setting_4"])
    
    mystic = await message.reply_text(_["auth_6"])
    text = _["auth_7"].format(message.chat.title)
    
    j = 0
    for auth_token in auth_names:
        _auth_data = await get_authuser(message.chat.id, auth_token)
        
        if not _auth_data:
            continue
            
        user_id = _auth_data["auth_user_id"]
        admin_id = _auth_data["admin_id"]
        admin_name = _auth_data["admin_name"]
        
        try:
            user_obj = await client.get_users(user_id)
            user_name = user_obj.first_name
            j += 1
        except Exception:
            continue
            
        text += f"{j}➤ {user_name} [<code>{user_id}</code>]\n"
        text += f"   {_['auth_8']} {admin_name} [<code>{admin_id}</code>]\n\n"
        
    await mystic.edit_text(text, reply_markup=close_markup(_))
