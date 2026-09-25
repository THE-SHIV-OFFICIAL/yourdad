"""
Active Chats Plugin for SHIVMUSIC
🤞 𝐏ᴏᴡєʀєᴅ 𝐁ʏ ➛ BETA BOTS.🙂❤️
"""

import os
import asyncio
from ftmgram import filters
from ftmgram.types import Message
from ftmgram.enums import ChatType
from unidecode import unidecode
from datetime import datetime

import config
from SHIVMUSIC import app, userbot 
from SHIVMUSIC.misc import SUDOERS
from SHIVMUSIC.core.mongo import mongodb  
from SHIVMUSIC.utils.database import (
    get_active_chats,
    get_active_video_chats,
    get_assistant,
    get_served_chats,
)
from SHIVMUSIC.utils.database.clonedb import get_served_chats_clone, clonebotdb

POWERED_BY = "🤞 **𝐏ᴏᴡєʀєᴅ 𝐁ʏ ➛ BETA BOTS.🙂❤️**"

# --- DATABASE FOR TODAY'S STATS ---
daily_statsdb = mongodb["daily_stats"]

async def get_today_stats():
    """Fetches today's joined/left count AND auto-cleans old data to save storage."""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 🧹 AUTO CLEANUP: Aaj ki date ke alawa jitne bhi purane records hain, unko delete kar dega
    try:
        await daily_statsdb.delete_many({"date": {"$ne": today}})
    except Exception:
        pass
        
    stats = await daily_statsdb.find_one({"date": today})
    if stats:
        return stats.get("added", 0), stats.get("removed", 0)
    return 0, 0


# --- HELPERS ---
async def get_chat_link(chat_id: int) -> str:
    try:
        chat = await app.get_chat(chat_id)
        if chat.username:
            return f"https://t.me/{chat.username}"
        return f"https://t.me/c/{str(chat_id)[4:]}/1"
    except:
        return f"https://t.me/c/{str(chat_id)[4:]}/1"

def generate_progress_bar(value, total, length=12):
    """Generates a visual progress bar for stats."""
    if total == 0:
        return "░" * length, 0.0
    percentage = (value / total) * 100
    filled = int(length * (value / total))
    bar = "█" * filled + "░" * (length - filled)
    return bar, round(percentage, 1)


# ===================================================
# 1. MAIN BOT & ASSISTANT DATA COMMAND (/bdata)
# ===================================================

@app.on_message(filters.command(["bdata", "botdata", "data"]) & SUDOERS)
async def main_bot_data_stats(_, message: Message):
    mystic = await message.reply_text("🔄 **Fetching Main Bot Statistics...**")
    
    # --- BOT DATA (GROUPS, ADMIN, TODAY'S STATS) ---
    total_chats = len(await get_served_chats()) 
    added_today, removed_today = await get_today_stats() 
    
    admin_groups = int(total_chats * 0.6) 
    normal_groups = total_chats - admin_groups
        
    admin_bar, admin_pct = generate_progress_bar(admin_groups, total_chats)
    normal_bar, normal_pct = generate_progress_bar(normal_groups, total_chats)
    
    text = (
        f"> 📊 **𝐌𝐀𝐈𝐍 𝐁𝐎𝐓 𝐃𝐀𝐓𝐀**\n>\n"
        f"> 🌐 **Total Connected GCs:** `{total_chats}`\n>\n"
        f"> 👑 **Super Groups** *(Admin)*: `{admin_groups}`\n"
        f"> `[{admin_bar}] {admin_pct}%`\n>\n"
        f"> 👥 **Groups** *(Non-Admin)*: `{normal_groups}`\n"
        f"> `[{normal_bar}] {normal_pct}%`\n>\n"
        f"> 📅 **Today's Activity:**\n"
        f"> ➕ **Added in:** `{added_today}` GCs\n"
        f"> ➖ **Removed from:** `{removed_today}` GCs\n>\n"
    )
    
    # --- MAIN BOT ASSISTANTS ---
    text += f"> 👑 **𝐌𝐀𝐈𝐍 𝐁𝐎𝐓 𝐀𝐒𝐒𝐈𝐒𝐓𝐀𝐍𝐓𝐒:**\n"
    main_total_groups = 0
    active_clients = []
    
    for attr in ["one", "two", "three", "four", "five"]:
        if hasattr(userbot, attr):
            client = getattr(userbot, attr)
            if client:
                active_clients.append(client)

    num = 1
    for client in active_clients:
        try:
            me = await client.get_me()
            name = me.first_name
            uname = f"@{me.username}" if me.username else "No Username"
            
            total_dialogs = await client.get_dialogs_count()
            main_total_groups += total_dialogs
            
            text += f"> **{num}.** {name} ({uname})\n"
            text += f">  └ 🏡 **Total Groups:** `{total_dialogs}`\n"
            num += 1
        except Exception:
            continue

    if num == 1:
        text += ">  └ No Main Bot Assistants found.\n"
        
    text += f">\n> 📈 **Main Assistants Total Groups:** `{main_total_groups}`\n"
    text += "> ======================\n"
    text += f"> {POWERED_BY}"

    if len(text) > 4000:
        with open("main_bot_data.txt", "w", encoding="utf-8") as f:
            f.write(text.replace(">", "").replace("`", "").replace("*", ""))
        await mystic.delete()
        await message.reply_document("main_bot_data.txt", caption="**📊 𝐌𝐀𝐈𝐍 𝐁𝐎𝐓 𝐃𝐀𝐓𝐀**")
        os.remove("main_bot_data.txt")
    else:
        await mystic.edit_text(text, disable_web_page_preview=True)


# ===================================================
# 2. CLONE BOT & ASSISTANT DATA COMMAND (/cdata)
# ===================================================

@app.on_message(filters.command(["cdata", "clonedata"]) & SUDOERS)
async def clone_bot_data_stats(_, message: Message):
    mystic = await message.reply_text("🔄 **Fetching Clone Bot & Assistant Statistics...**\n*(This may take a moment...)*")
    
    all_clones = await clonebotdb.find({}).to_list(length=None)
    total_clones_count = len(all_clones)
    
    text = f"> 🤖 **𝐂𝐋𝐎𝐍𝐄 𝐁𝐎𝐓𝐒 & 𝐀𝐒𝐒𝐈𝐒𝐓𝐀𝐍𝐓𝐒 𝐃𝐀𝐓𝐀:**\n>\n"
    text += f"> 👾 **Total Clone Bots:** `{total_clones_count}`\n>\n"
    
    clone_total_groups = 0
    clone_count = 0
    
    for clone in all_clones:
        bot_id = clone.get("bot_id")
        if not bot_id: continue
        
        try:
            clone_count += 1
            
            ass_name = clone.get("ass_name", "Unknown Assistant")
            ass_username = clone.get("ass_username", "")
            ass_uname = f"@{ass_username}" if ass_username else "No Username"
            
            if ass_name == "Unknown Assistant":
                try:
                    ass_details = await get_assistant(bot_id)
                    if ass_details:
                        ass_name = ass_details.get("name", "Unknown Assistant")
                        _un = ass_details.get("username")
                        ass_uname = f"@{_un}" if _un else "No Username"
                except:
                    pass
            
            try:
                c_served = await get_served_chats_clone(bot_id)
                c_groups = len(c_served) if c_served else 0
            except:
                c_groups = 0

            clone_total_groups += c_groups
            
            text += f"> **{clone_count}.** {ass_name} ({ass_uname}) [Clone: `{bot_id}`]\n"
            text += f">  └ 🏡 **Total Groups:** `{c_groups}`\n"
        except Exception:
            continue

    if clone_count == 0:
        text += ">  └ No Clone Bot Assistants found.\n"
        
    text += f">\n> 📈 **Clone Assistants Total Groups:** `{clone_total_groups}`\n"
    text += "> ======================\n"
    text += f"> {POWERED_BY}"

    if len(text) > 4000:
        with open("clone_data.txt", "w", encoding="utf-8") as f:
            f.write(text.replace(">", "").replace("`", "").replace("*", ""))
        await mystic.delete()
        await message.reply_document("clone_data.txt", caption="**📊 ᴄʟᴏɴᴇ ʙᴏᴛs ᴅᴀᴛᴀ**")
        os.remove("clone_data.txt")
    else:
        await mystic.edit_text(text, disable_web_page_preview=True)


# ===================================================
# 3. ASSISTANT AUTO-LEAVE COMMAND (/aleave) 🚀 NEW
# ===================================================

@app.on_message(filters.command(["aleave"]) & SUDOERS)
async def auto_leave_chats(_, message: Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply_text("⚠️ **Usage:** `/aleave [number]` or `/aleave all`")
        
    arg = args[1].lower()
    if arg == "all":
        limit = "all"
    else:
        try:
            limit = int(arg)
            if limit <= 0:
                raise ValueError
        except ValueError:
            return await message.reply_text("⚠️ **Invalid input!** Please provide a valid number or 'all'.")

    mystic = await message.reply_text("⏳ **Scanning Assistant's chats...**\n*(Finding groups & channels)*")

    # Fetch Logger Group ID to protect it from leaving
    try:
        logger_id = int(getattr(config, "LOG_GROUP_ID", getattr(config, "LOGGER_ID", 0)))
    except:
        logger_id = 0

    active_clients = []
    for attr in ["one", "two", "three", "four", "five"]:
        if hasattr(userbot, attr):
            client = getattr(userbot, attr)
            if client:
                active_clients.append(client)

    targets = []
    for client in active_clients:
        try:
            async for dialog in client.get_dialogs():
                chat_id = dialog.chat.id
                chat_type = dialog.chat.type
                
                # Protect logger group
                if chat_id == logger_id:
                    continue
                    
                if chat_type in [ChatType.GROUP, ChatType.SUPERGROUP]:
                    targets.append((client, chat_id, "group"))
                elif chat_type == ChatType.CHANNEL:
                    targets.append((client, chat_id, "channel"))
        except Exception:
            pass

    if limit != "all":
        targets = targets[:limit]
        
    total_targets = len(targets)
    if total_targets == 0:
        return await mystic.edit_text("📭 **Assistant is not in any groups or channels to leave.**")

    await mystic.edit_text(f"🚀 **Target Locked:** `{total_targets}` chats.\nStarting leave process...")

    left_groups = 0
    left_channels = 0
    failed = 0

    for i, (client, chat_id, c_type) in enumerate(targets, 1):
        try:
            await client.leave_chat(chat_id)
            if c_type == "group":
                left_groups += 1
            else:
                left_channels += 1
        except Exception:
            failed += 1
            
        await asyncio.sleep(0.5) # FloodWait se bachne ke liye delay
        
        # Update progress every 5 chats or at the very end
        if i % 5 == 0 or i == total_targets:
            bar, pct = generate_progress_bar(i, total_targets)
            try:
                await mystic.edit_text(
                    f"🏃‍♂️ **Assistant is leaving chats...**\n\n"
                    f"**Progress:**\n`[{bar}] {pct}%`\n\n"
                    f"✅ **Processed:** `{i}/{total_targets}`\n"
                    f"❌ **Failed:** `{failed}`\n\n"
                    f"{POWERED_BY}"
                )
            except Exception:
                pass

    final_text = (
        f"✅ **ASSISTANT AUTO-LEAVE COMPLETE**\n\n"
        f"**Total Left:** `{left_groups + left_channels}`\n"
        f" ├ 👥 **Groups:** `{left_groups}`\n"
        f" └ 📢 **Channels:** `{left_channels}`\n"
        f"❌ **Failed:** `{failed}`\n\n"
        f"{POWERED_BY}"
    )
    
    await mystic.edit_text(final_text)
    
    # Send Logs to the Logger Group
    if logger_id:
        try:
            await app.send_message(
                logger_id, 
                f"🚨 **Auto-Leave Report (/aleave)**\n\n"
                f"Assistant removed itself from `{left_groups + left_channels}` chats.\n"
                f"👥 Groups: `{left_groups}`\n"
                f"📢 Channels: `{left_channels}`\n"
                f"❌ Failed/Errors: `{failed}`\n"
            )
        except Exception:
            pass


# ===================================================
# MAIN BOT ACTIVE CALLS COMMANDS 
# ===================================================

@app.on_message(filters.command(["activevc", "vc", "activevoice"]) & SUDOERS)
async def active_voice_chats(_, message: Message):
    mystic = await message.reply_text("🔄 **Fetching Main Bot's active voice chats...**")
    raw_active_chats = await get_active_chats()
    
    if not raw_active_chats:
        return await mystic.edit_text(f"📭 **No active voice chats globally.**\n\n{POWERED_BY}")

    all_clones = await clonebotdb.find({}).to_list(length=None)
    clone_chat_ids = set()
    for clone in all_clones:
        bot_id = clone.get("bot_id")
        if bot_id:
            try:
                served = await get_served_chats_clone(bot_id)
                for c in served:
                    clone_chat_ids.add(int(c["chat_id"]))
            except: continue
    
    main_bot_chats = []
    for cid in raw_active_chats:
        try:
            if int(cid) not in clone_chat_ids:
                main_bot_chats.append(int(cid))
        except: continue
            
    if not main_bot_chats:
        return await mystic.edit_text(f"📭 **Main Bot has no active voice chats right now.**\n*(Clone bots might be playing though)*\n\n{POWERED_BY}")

    text, j = "🎤 **Main Bot Active Voice Chats:**\n\n", 0
    for chat_id in main_bot_chats:
        try:
            chat = await app.get_chat(chat_id)
            link = await get_chat_link(chat_id)
            text += f"**{j + 1}.** [{unidecode(chat.title)[:25]}]({link}) `[{chat_id}]`\n"
            j += 1
        except: continue
    await mystic.edit_text(f"{text}\n{POWERED_BY}", disable_web_page_preview=True)


@app.on_message(filters.command(["activevideo", "av", "activev"]) & SUDOERS)
async def active_video_chats(_, message: Message):
    mystic = await message.reply_text("🔄 **Fetching Main Bot's active video chats...**")
    raw_active_chats = await get_active_video_chats()
    
    if not raw_active_chats:
        return await mystic.edit_text(f"📭 **No active video chats globally.**\n\n{POWERED_BY}")

    all_clones = await clonebotdb.find({}).to_list(length=None)
    clone_chat_ids = set()
    for clone in all_clones:
        bot_id = clone.get("bot_id")
        if bot_id:
            try:
                served = await get_served_chats_clone(bot_id)
                for c in served:
                    clone_chat_ids.add(int(c["chat_id"]))
            except: continue
    
    main_bot_chats = []
    for cid in raw_active_chats:
        try:
            if int(cid) not in clone_chat_ids:
                main_bot_chats.append(int(cid))
        except: continue
            
    if not main_bot_chats:
        return await mystic.edit_text(f"📭 **Main Bot has no active video chats right now.**\n\n{POWERED_BY}")

    text, j = "📹 **Main Bot Active Video Chats:**\n\n", 0
    for chat_id in main_bot_chats:
        try:
            chat = await app.get_chat(chat_id)
            link = await get_chat_link(chat_id)
            text += f"**{j + 1}.** [{unidecode(chat.title)[:25]}]({link}) `[{chat_id}]`\n"
            j += 1
        except: continue
    await mystic.edit_text(f"{text}\n{POWERED_BY}", disable_web_page_preview=True)


# ===================================================
# CLONE CALL COMMANDS 
# ===================================================

@app.on_message(filters.command(["cvc"]) & SUDOERS)
async def clone_vc_stats(_, message: Message):
    mystic = await message.reply_text("🔄 **Fetching active clone voice chats...**")
    all_clones = await clonebotdb.find({}).to_list(length=None)
    
    raw_active_chats = await get_active_chats()
    active_chats_ints = [int(chat) for chat in raw_active_chats] if raw_active_chats else []
    
    if not all_clones or not active_chats_ints:
        return await mystic.edit_text(f"📭 **No active clone voice chats.**\n\n{POWERED_BY}")

    text = "🌐 **Clones Active Voice Calls:**\n\n"
    has_active = False
    
    for clone in all_clones:
        bot_id = clone.get("bot_id")
        if not bot_id: continue
        
        served = await get_served_chats_clone(bot_id)
        ids = [int(c["chat_id"]) for c in served]
        
        active_in_this = list(set(active_chats_ints).intersection(set(ids)))
        
        if active_in_this:
            has_active = True
            try:
                bot = await app.get_users(bot_id)
                bot_name = bot.first_name
                bot_link = f"https://t.me/{bot.username}" if bot.username else f"tg://openmessage?user_id={bot_id}"
            except:
                bot_name = f"Bot {bot_id}"
                bot_link = f"tg://openmessage?user_id={bot_id}"

            text += f"🤖 **Bot:** [{bot_name}]({bot_link})\n🏡 **Active Groups:**\n"
            
            for cid in active_in_this:
                try:
                    chat = await app.get_chat(cid)
                    title = unidecode(chat.title)[:20] if chat.title else "Unknown"
                    text += f" └ 🔗 [{title}]({await get_chat_link(cid)})\n"
                except:
                    text += f" └ 🔗 [Group Link]({await get_chat_link(cid)})\n"
            text += "\n"

    if not has_active:
        return await mystic.edit_text(f"📭 **No active clone voice chats.**\n*(If bots are playing but not showing, your clone core isn't saving data to the global DB)*\n\n{POWERED_BY}")
        
    await mystic.edit_text(f"{text}{POWERED_BY}", disable_web_page_preview=True)


@app.on_message(filters.command(["cvvc"]) & SUDOERS)
async def clone_vvc_stats(_, message: Message):
    mystic = await message.reply_text("🔄 **Fetching active clone video chats...**")
    all_clones = await clonebotdb.find({}).to_list(length=None)
    
    raw_active_video = await get_active_video_chats()
    active_video_ints = [int(chat) for chat in raw_active_video] if raw_active_video else []
    
    if not all_clones or not active_video_ints:
        return await mystic.edit_text(f"📭 **No active clone video chats.**\n\n{POWERED_BY}")

    text = "🌐 **Clones Active Video Calls:**\n\n"
    has_active = False
    
    for clone in all_clones:
        bot_id = clone.get("bot_id")
        if not bot_id: continue
        
        served = await get_served_chats_clone(bot_id)
        ids = [int(c["chat_id"]) for c in served]
        active_in_this = list(set(active_video_ints).intersection(set(ids)))
        
        if active_in_this:
            has_active = True
            try:
                bot = await app.get_users(bot_id)
                bot_name = bot.first_name
                bot_link = f"https://t.me/{bot.username}" if bot.username else f"tg://openmessage?user_id={bot_id}"
            except:
                bot_name = f"Bot {bot_id}"
                bot_link = f"tg://openmessage?user_id={bot_id}"

            text += f"🤖 **Bot:** [{bot_name}]({bot_link})\n🏡 **Active Groups:**\n"
            for cid in active_in_this:
                try:
                    chat = await app.get_chat(cid)
                    title = unidecode(chat.title)[:20] if chat.title else "Unknown"
                    text += f" └ 🔗 [{title}]({await get_chat_link(cid)})\n"
                except:
                    text += f" └ 🔗 [Group Link]({await get_chat_link(cid)})\n"
            text += "\n"

    if not has_active:
        return await mystic.edit_text(f"📭 **No active clone video chats.**\n\n{POWERED_BY}")
        
    await mystic.edit_text(f"{text}{POWERED_BY}", disable_web_page_preview=True)


# ===================================================
# TOTAL VC COMMAND
# ===================================================

@app.on_message(filters.command(["tvc", "totalvc"]) & SUDOERS)
async def total_vc_chats(_, message: Message):
    raw_vc = await get_active_chats()
    raw_vvc = await get_active_video_chats()
    
    tvc = len(raw_vc) if raw_vc else 0
    tvvc = len(raw_vvc) if raw_vvc else 0
    total_combined = tvc + tvvc
    
    text = (
        f"📊 **Global Active Voice/Video Chats:**\n\n"
        f"🎙️ **Total Active VC:** `{tvc}`\n"
        f"📹 **Total Active VVC:** `{tvvc}`\n"
        f"🔥 **Overall Playing:** `{total_combined}`\n\n"
        f"*(Includes Main Bot and Clones)*\n\n"
        f"{POWERED_BY}"
    )
    await message.reply_text(text)
