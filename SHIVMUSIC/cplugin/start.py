import time
import random
import asyncio
import logging
from html import escape
from ftmgram import filters, Client
from ftmgram.enums import ChatType, ParseMode, ButtonStyle
from ftmgram.types import InlineKeyboardMarkup, Message, InputMediaPhoto, InputMediaVideo, InlineKeyboardButton
from youtubesearchpython.__future__ import VideosSearch

import config
from SHIVMUSIC import app
from SHIVMUSIC.misc import _boot_
from SHIVMUSIC.plugins.sudo.sudoers import sudoers_list
from SHIVMUSIC.utils.formatters import get_readable_time
from SHIVMUSIC.utils.rich_helper import markdown_to_html, stream_typewriter_rich_message

# Config Imports
from config import BANNED_USERS, OWNER_ID, START_IMG_URL, CMBOT, EFFECT_ID

# Module Imports
from SHIVMUSIC.utils.decorators.language import LanguageStart, languageCB
from strings import get_string
from SHIVMUSIC.utils.database.clonedb import get_owner_id_from_db, get_cloned_support_chat, get_cloned_support_channel
from SHIVMUSIC.utils.database import add_served_user_clone, add_served_chat_clone
from SHIVMUSIC.utils.database import clonebotdb

# Extra Import for Transfer Logic
from SHIVMUSIC.core.mongo import mongodb
cloneownerdb = mongodb.cloneownerdb

# Initialize logging
LOG = logging.getLogger(__name__)

# 💎 Premium Emojis List for Buttons (icon_custom_emoji_id)
PREMIUM_EMOJIS = [
    "5258362837411045098", "6102938383456146362", "5463274047771000031", "6100397162976252509",
    "5373310679241466020", "5408916593780470262", "5776182936638329359", "5258389041006518073",
    "6280269890821558384", "5936143551854285132", "6172332822892647766", "5891211339170326418",
    "5409368076447657845", "6172312314423808834", "6082387600599944892", "6271537028307881531"
]

# 🎨 Dynamic Color Generator (Random Styles)
def get_style_map():
    styles = [ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER]
    random.shuffle(styles)
    return {1: styles[0], 2: styles[1], 3: styles[2]}

# 🔘 Smart Button Creator
def create_btn(text, cb=None, url=None, user_id=None, style=ButtonStyle.PRIMARY, no_emoji=False):
    kwargs = {"text": text, "style": style}
    if cb: kwargs["callback_data"] = cb
    if url: kwargs["url"] = url
    if user_id: kwargs["user_id"] = user_id
    if not no_emoji: kwargs["icon_custom_emoji_id"] = int(random.choice(PREMIUM_EMOJIS))
    return InlineKeyboardButton(**kwargs)


# =====================================================================
# INTERNAL BUTTON HELPERS (SMART OWNER LOGIC)
# =====================================================================

async def get_safe_owner_button(client, text, user_id, username=None, style=ButtonStyle.PRIMARY):
    """
    1. Pehle ID se try karega.
    2. Agar ID fail ho gayi, toh Username se try karega.
    3. Agar dono fail ho gaye, toh chup chap 'None' return karega (No Error!).
    """
    if not user_id and not username:
        return None
        
    try:
        if user_id:
            # Bot ID se user ko cache karega
            user = await client.get_users(user_id)
            return create_btn(text=text, user_id=user.id, style=style)
    except Exception:
        pass # ID fail ho gayi, aage badho
        
    try:
        if username:
            # Bot Username se user ko cache karega
            user = await client.get_users(username)
            return create_btn(text=text, user_id=user.id, style=style)
    except Exception:
        pass # Username bhi fail ho gaya
        
    # Dono fail hone par None return hoga, taaki bot crash na ho
    return None


async def make_start_panel(client, bot_username, owner_id, owner_username, 
                           txt_add, txt_support, txt_channel, txt_owner, txt_help, 
                           support_chat, support_channel,
                           custom_btn=None, btn_pos="TOP"):
    
    s_map = get_style_map()
    buttons = []

    # 1. Add to Group
    if txt_add != "HIDDEN":
        buttons.append([create_btn(text=txt_add, url=f"https://t.me/{bot_username}?startgroup=true", style=s_map[1])])

    # 2. Help Button
    if txt_help != "HIDDEN":
        buttons.append([create_btn(text=txt_help, cb="settings_back_helper", style=s_map[1])])

    # 3. Support & Channel
    row_support = []
    if txt_support != "HIDDEN":
        row_support.append(create_btn(text=txt_support, url=support_chat, style=s_map[2]))
    if txt_channel != "HIDDEN":
        row_support.append(create_btn(text=txt_channel, url=support_channel, style=s_map[2]))
    if row_support:
        buttons.append(row_support)

    # 4. Owner Button (SAFE LOGIC)
    if txt_owner != "HIDDEN":
        owner_btn = await get_safe_owner_button(client, txt_owner, owner_id, owner_username, style=s_map[1])
        if owner_btn:
            buttons.append([owner_btn])
        # Agar owner_btn 'None' return hota hai, toh button banega hi nahi (crash hone ka koi chance hi nahi)

    # --- Custom Button Logic ---
    if custom_btn and custom_btn.get("text"):
        btn_url = custom_btn.get("url", "").strip()
        
        if btn_url and not btn_url.startswith(("http://", "https://", "tg://")):
            btn_url = f"https://{btn_url}"
        elif not btn_url:
            btn_url = "https://t.me/Telegram"
            
        c_btn = create_btn(text=custom_btn["text"], url=btn_url, style=s_map[3])
        
        if btn_pos in ["UP", "TOP"]:
            buttons.insert(0, [c_btn])
        elif btn_pos in ["DOWN", "BOTTOM"]:
            buttons.append([c_btn])
        elif btn_pos in ["MID", "MIDDLE"]:
            if len(buttons) >= 1:
                buttons.insert(1, [c_btn])
            else:
                buttons.append([c_btn])
        elif btn_pos == "LEFT":
             if buttons and isinstance(buttons[0], list): buttons[0].insert(0, c_btn)
             else: buttons.insert(0, [c_btn])
        elif btn_pos == "RIGHT":
             if buttons and isinstance(buttons[0], list): buttons[0].append(c_btn)
             else: buttons.insert(0, [c_btn])
        else:
            buttons.insert(0, [c_btn])

    return InlineKeyboardMarkup(buttons)


def make_gp_panel(bot_username, txt_add, txt_support, support_chat):
    s_map = get_style_map()
    buttons = [
        [
            create_btn(text=txt_add, url=f"https://t.me/{bot_username}?startgroup=true", style=s_map[2]),
            create_btn(text=txt_support, url=support_chat, style=s_map[2]),
        ]
    ]
    return InlineKeyboardMarkup(buttons)

# =====================================================================
# Database Helpers
# =====================================================================

async def get_start_image(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_image")

async def get_start_caption(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_caption")

async def get_start_button(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_button")

async def get_start_btn_pos(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_btn_pos", "TOP")

async def get_start_video(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_video")

async def get_start_sticker(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_sticker")

async def get_start_animation(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_animation")

async def get_start_reaction(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_reaction")

async def get_start_effect(bot_id):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get("start_effect")

async def get_custom_btn_text(bot_id, key, default_text):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    return d.get(f"btn_{key}", default_text)

# ✅ Helper to Add Random Content
async def add_start_content(bot_id, key, value):
    d = await clonebotdb.find_one({"bot_id": bot_id}) or {}
    current = d.get(key)
    
    if current:
        if isinstance(current, dict):
            current = f"{current['text']} - {current['url']}" 

        if str(value) in str(current).split("|||"):
            return False 
        final_value = f"{current}|||{value}"
    else:
        final_value = value
        
    await clonebotdb.update_one({"bot_id": bot_id}, {"$set": {key: final_value}}, upsert=True)
    return True

# --- General Helpers ---

def format_link(val):
    if not val or str(val).strip() in ["", "none", "None"]:
        return "https://t.me/Telegram" 
    val = str(val).strip()
    if val.startswith("@"):
        val = val[1:] 
    if val.startswith(("https://", "http://", "tg://")):
        return val
    return f"https://t.me/{val}"

def get_mention_html(user_id, name):
    return f'<a href="tg://user?id={user_id}">{name}</a>'

# =====================================================================
# START COMMAND (PRIVATE)
# =====================================================================

@Client.on_message(filters.command("start") & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    a = await client.get_me()
    bot_id = a.id
    await add_served_user_clone(message.from_user.id, bot_id)

    # 1. Loading Animation
    raw_sticker, raw_animation = await asyncio.gather(
        get_start_sticker(bot_id),
        get_start_animation(bot_id)
    )
    
    custom_sticker = random.choice(raw_sticker.split("|||")) if raw_sticker else None
    custom_animation = random.choice(raw_animation.split("|||")) if raw_animation else None
    
    loading = None

    if custom_sticker:
        try:
            loading = await message.reply_sticker(custom_sticker)
            await asyncio.sleep(2)
        except:
            pass
    elif custom_animation:
        try:
            loading = await message.reply_animation(custom_animation)
            await asyncio.sleep(2)
        except:
             pass
    else:
        try:
            loading_html = (
                "<blockquote><b><tg-emoji emoji-id=\"6172312314423808834\">✨</tg-emoji> "
                f"{escape(a.first_name)} <tg-emoji emoji-id=\"6082387600599944892\">🎧</tg-emoji></b><br/>"
                "<i>Preparing your music player...</i><br/>"
                "<b>Loading clone settings and playback controls</b></blockquote>"
            )
            loading = await stream_typewriter_rich_message(
                client,
                message.chat.id,
                loading_html,
                reply_to_message_id=message.id,
                chunk_delay=0.08,
            )
        except:
            pass

    # ✅ Fetch All Data properly
    (
        C_BOT_OWNER_ID,
        raw_support,
        raw_channel,
        txt_add,
        txt_support,
        txt_channel,
        txt_owner,
        txt_help,
        raw_custom_btn,
        btn_pos,
        raw_video,
        raw_img,      
        raw_caption,
        raw_reaction,
        raw_effect
    ) = await asyncio.gather(
        get_owner_id_from_db(bot_id),
        get_cloned_support_chat(bot_id),
        get_cloned_support_channel(bot_id),
        get_custom_btn_text(bot_id, "add", _["S_B_3"]),
        get_custom_btn_text(bot_id, "support", _["S_B_9"]),
        get_custom_btn_text(bot_id, "channel", _["S_B_6"]),
        get_custom_btn_text(bot_id, "owner", _["C_B_2"]),
        get_custom_btn_text(bot_id, "help", _["S_B_4"]),
        get_start_button(bot_id),
        get_start_btn_pos(bot_id),
        get_start_video(bot_id),
        get_start_image(bot_id), 
        get_start_caption(bot_id),
        get_start_reaction(bot_id),
        get_start_effect(bot_id),
    )

    C_SUPPORT_CHAT = format_link(raw_support)
    C_SUPPORT_CHANNEL = format_link(raw_channel)

    # ✅ RANDOM REACTION LOGIC
    if raw_reaction:
        reaction_emoji = random.choice(raw_reaction.split("|||"))
    else:
        reaction_emoji = random.choice(["🔥", "❤️", "🥰", "😍", "👍", "⚡", "🎉"])
    
    try:
        await message.react(reaction_emoji)
    except:
        pass

    try:
        if loading: await loading.delete()
    except:
        pass

    # Inline Arguments Help Data
    s_map = get_style_map()
    if len(message.text.split()) > 1:
        arg = message.text.split(None, 1)[1]
        
        if arg.startswith("help"):
            keyboard = InlineKeyboardMarkup([[create_btn(text=_["S_B_9"], url=C_SUPPORT_CHAT, style=s_map[1])]])
            help_photo = None
            if raw_img:
                help_photo = random.choice(raw_img.split("|||"))
            if not help_photo:
                try:
                    async for p in client.get_chat_photos(message.from_user.id, limit=1):
                        help_photo = p.file_id
                        break
                except:
                    pass
            if not help_photo:
                help_photo = random.choice(["https://n.uguu.se/GvQQwulv.jpg", "https://d.uguu.se/nVKJFsNv.jpg", "https://n.uguu.se/CSSeXVzQ.jpg", "https://d.uguu.se/pBwORuAH.jpg"])
                
            return await message.reply_photo(
                photo=help_photo,
                caption=_["help_1"].format(C_SUPPORT_CHAT),
                reply_markup=keyboard,
                has_spoiler=True
            )
            
        if arg.startswith("sud"):
            return await sudoers_list(client=client, message=message, _=_)
            
        if arg.startswith("inf"):
            m = await message.reply_text("<tg-emoji emoji-id='5429571366384842791'>🔎</tg-emoji>")
            q = arg.replace("info_", "", 1)
            try:
                results = await VideosSearch(f"https://www.youtube.com/watch?v={q}", limit=1).next()
                result = results["result"][0]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                caption = _["start_6"].format(result["title"], result["duration"], result["viewCount"]["short"], result["publishedTime"], result["channel"]["link"], result["channel"]["name"], a.mention)
                
                key = InlineKeyboardMarkup([
                    [
                        create_btn(text=_["S_B_8"], url=result["link"], style=s_map[2]), 
                        create_btn(text=_["S_B_9"], url=C_SUPPORT_CHAT, style=s_map[2])
                    ]
                ])
                await m.delete()
                return await message.reply_photo(photo=thumbnail, caption=caption, reply_markup=key, has_spoiler=True)
            except Exception as e:
                LOG.error(e)
                return await m.edit_text("<tg-emoji emoji-id='6271611232457855630'>❌</tg-emoji> Error fetching info.")

    # Custom Button Data Logic
    custom_button_data = None
    if raw_custom_btn:
        if isinstance(raw_custom_btn, dict):
            custom_button_data = raw_custom_btn
        elif isinstance(raw_custom_btn, str):
            chosen_str = random.choice(raw_custom_btn.split("|||"))
            if "-" in chosen_str:
                txt, url = chosen_str.split("-", 1)
                custom_button_data = {"text": txt.strip(), "url": url.strip()}
    
    # 🔗 ASYNC Start Panel (Safe Owner Fallbacks)
    owner_username = getattr(config, "OWNER_USERNAME", None)
    
    markup = await make_start_panel(
        client=client, 
        bot_username=a.username, 
        owner_id=C_BOT_OWNER_ID, 
        owner_username=owner_username,
        txt_add=txt_add, 
        txt_support=txt_support, 
        txt_channel=txt_channel, 
        txt_owner=txt_owner, 
        txt_help=txt_help,
        support_chat=C_SUPPORT_CHAT, 
        support_channel=C_SUPPORT_CHANNEL,
        custom_btn=custom_button_data, 
        btn_pos=btn_pos
    )

    # 🟢 Custom Start Caption Logic
    user_mention = get_mention_html(message.from_user.id, message.from_user.first_name)
    bot_mention = get_mention_html(a.id, a.first_name)
    
    if raw_caption:
        caption_template = random.choice(raw_caption.split("|||"))
        caption = caption_template.replace("{name}", user_mention)\
                                  .replace("{firstname}", message.from_user.first_name)\
                                  .replace("{botname}", bot_mention)\
                                  .replace("{username}", a.username)
    else:
        bot_name_upper = a.first_name.upper()
        caption = (
            f"<b>───[ ˹ {bot_name_upper} ˼ 🎵 ]───</b>\n\n"
            f"<b>Hᴏʟᴏᴏ - !! <tg-spoiler>{user_mention}</tg-spoiler></b>\n\n"
            f"<b>I ᴀᴍ ᴛʜᴇ ғᴀsᴛ ᴀɴᴅ ᴘᴏᴡᴇʀғᴜʟ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ʙᴏᴛ ᴡɪᴛʜ sᴏᴍᴇ ᴀᴡᴇsᴏᴍᴇ ғᴇᴀᴛᴜʀᴇs.</b>\n\n"
            f"<blockquote>"
            f"<b>🎶 ʜɪɢʜ-ǫᴜᴧʟɪᴛʏ ᴍᴜꜱɪᴄ ᴘʟᴧʏєʀ ʙσᴛ</b>\n"
            f"<b>ғσʀ ᴛєʟєɢʀᴧϻ ɢʀσᴜᴘꜱ & ᴄʜᴧηηєʟꜱ</b>\n\n"
            f"<b>🔥 ɪηꜱᴛᴧηᴛ ꜱᴛʀєᴧϻɪηɢ</b>\n"
            f"<b>❤️ ꜱϻσσᴛʜ ᴘʟᴧʏʙᴧᴄᴋ</b>\n"
            f"<b>🎧 ᴄʀʏꜱᴛᴧʟ ꜱσᴜηᴅ | ησ ʟᴧɢ</b>"
            f"</blockquote>\n\n"
            f"<b>Cʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇs ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅs.</b>"
        )

    # Base payload settings
    effect_id = random.choice(raw_effect.split("|||")) if raw_effect else None
    send_kwargs = {
        "caption": caption,
        "reply_markup": markup,
        "has_spoiler": True,
        "parse_mode": ParseMode.HTML
    }
    if effect_id:
        send_kwargs["effect_id"] = effect_id

    # 🎥 Video Logic Check
    start_video = random.choice(raw_video.split("|||")) if raw_video else None
    if start_video:
        try:
            return await message.reply_video(start_video, **send_kwargs)
        except:
            pass
            
    # 📸 SMART PHOTO LOGIC
    photo = None
    start_img = random.choice(raw_img.split("|||")) if raw_img else None
    
    if start_img:
        photo = start_img
    else:
        try:
            async for p in client.get_chat_photos(message.from_user.id, limit=1):
                photo = p.file_id
                break
        except:
            pass
            
        if not photo:
            photo = random.choice([
                "https://n.uguu.se/GvQQwulv.jpg",
                "https://d.uguu.se/nVKJFsNv.jpg",
                "https://n.uguu.se/CSSeXVzQ.jpg",
                "https://d.uguu.se/pBwORuAH.jpg"
            ])

    send_kwargs["caption"] = markdown_to_html(send_kwargs["caption"])
    await message.reply_photo(photo, **send_kwargs)

# =====================================================================
# START COMMAND (GROUP)
# =====================================================================

@Client.on_message(filters.command("start") & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    a = await client.get_me()
    bot_id = a.id
    uptime = get_readable_time(int(time.time() - _boot_))
    
    raw_support, txt_add, txt_support, raw_video, raw_img = await asyncio.gather(
        get_cloned_support_chat(a.id),
        get_custom_btn_text(a.id, "add", _["S_B_1"]),
        get_custom_btn_text(a.id, "support", _["S_B_2"]),
        get_start_video(bot_id),
        get_start_image(bot_id)
    )

    C_SUPPORT_CHAT = format_link(raw_support)
    markup = make_gp_panel(a.username, txt_add, txt_support, C_SUPPORT_CHAT)
    caption = markdown_to_html(_["start_1"].format(a.mention, uptime))
    
    start_video = random.choice(raw_video.split("|||")) if raw_video else None
    if start_video:
        try:
            return await message.reply_video(
                start_video,
                caption=caption,
                reply_markup=markup,
                has_spoiler=True,
                parse_mode=ParseMode.HTML,
            )
        except:
            pass
            
    # 📸 SMART PHOTO LOGIC
    photo = None
    start_img = random.choice(raw_img.split("|||")) if raw_img else None
    
    if start_img:
        photo = start_img
    else:
        try:
            async for p in client.get_chat_photos(message.from_user.id, limit=1):
                photo = p.file_id
                break
        except:
            pass
            
        if not photo:
            photo = random.choice([
                "https://n.uguu.se/GvQQwulv.jpg",
                "https://d.uguu.se/nVKJFsNv.jpg",
                "https://n.uguu.se/CSSeXVzQ.jpg",
                "https://d.uguu.se/pBwORuAH.jpg"
            ])

    await message.reply_photo(
        photo,
        caption=caption,
        reply_markup=markup,
        has_spoiler=True,
        parse_mode=ParseMode.HTML,
    )
    await add_served_chat_clone(message.chat.id, a.id)

# =====================================================================
# CALLBACKS & FAST ACTIONS (Super Fast Back Button)
# =====================================================================

@Client.on_callback_query(filters.regex("settingsback_home") & ~BANNED_USERS)
@languageCB
async def home_back_handler(client, CallbackQuery, _):
    a = await client.get_me()
    bot_id = a.id

    (
        C_BOT_OWNER_ID,
        raw_support,
        raw_channel,
        txt_add,
        txt_support,
        txt_channel,
        txt_owner,
        txt_help,
        raw_custom_btn,
        btn_pos,
        raw_video,
        raw_img,      
        raw_caption,
        raw_effect
    ) = await asyncio.gather(
        get_owner_id_from_db(bot_id),
        get_cloned_support_chat(bot_id),
        get_cloned_support_channel(bot_id),
        get_custom_btn_text(bot_id, "add", _["S_B_3"]),
        get_custom_btn_text(bot_id, "support", _["S_B_9"]),
        get_custom_btn_text(bot_id, "channel", _["S_B_6"]),
        get_custom_btn_text(bot_id, "owner", _["C_B_2"]),
        get_custom_btn_text(bot_id, "help", _["S_B_4"]),
        get_start_button(bot_id),
        get_start_btn_pos(bot_id),
        get_start_video(bot_id),
        get_start_image(bot_id),
        get_start_caption(bot_id),
        get_start_effect(bot_id),
    )

    C_SUPPORT_CHAT = format_link(raw_support)
    C_SUPPORT_CHANNEL = format_link(raw_channel)

    custom_button_data = None
    if raw_custom_btn:
        if isinstance(raw_custom_btn, dict):
            custom_button_data = raw_custom_btn
        elif isinstance(raw_custom_btn, str):
            chosen_str = random.choice(raw_custom_btn.split("|||"))
            if "-" in chosen_str:
                txt, url = chosen_str.split("-", 1)
                custom_button_data = {"text": txt.strip(), "url": url.strip()}
    
    # 🔗 ASYNC Start Panel logic
    owner_username = getattr(config, "OWNER_USERNAME", None)
    
    markup = await make_start_panel(
        client=client, 
        bot_username=a.username, 
        owner_id=C_BOT_OWNER_ID, 
        owner_username=owner_username,
        txt_add=txt_add, 
        txt_support=txt_support, 
        txt_channel=txt_channel, 
        txt_owner=txt_owner, 
        txt_help=txt_help,
        support_chat=C_SUPPORT_CHAT, 
        support_channel=C_SUPPORT_CHANNEL,
        custom_btn=custom_button_data, 
        btn_pos=btn_pos
    )
    
    user_mention = get_mention_html(CallbackQuery.from_user.id, CallbackQuery.from_user.first_name)
    bot_mention = get_mention_html(a.id, a.first_name)
    
    if raw_caption:
        caption_template = random.choice(raw_caption.split("|||"))
        caption = caption_template.replace("{name}", user_mention)\
                                  .replace("{firstname}", CallbackQuery.from_user.first_name)\
                                  .replace("{botname}", bot_mention)\
                                  .replace("{username}", a.username)
    else:
        bot_name_upper = a.first_name.upper()
        caption = (
            f"<b>───[ ˹ {bot_name_upper} ˼ 🎵 ]───</b>\n\n"
            f"<b>Hᴏʟᴏᴏ - !! <tg-spoiler>{user_mention}</tg-spoiler></b>\n\n"
            f"<b>I ᴀᴍ ᴛʜᴇ ғᴀsᴛ ᴀɴᴅ ᴘᴏᴡᴇʀғᴜʟ ᴍᴜsɪᴄ ᴘʟᴀʏᴇʀ ʙᴏᴛ ᴡɪᴛʜ sᴏᴍᴇ ᴀᴡᴇsᴏᴍᴇ ғᴇᴀᴛᴜʀᴇs.</b>\n\n"
            f"<blockquote>"
            f"<b>🎶 ʜɪɢʜ-ǫᴜᴧʟɪᴛʏ ᴍᴜꜱɪᴄ ᴘʟᴧʏєʀ ʙσᴛ</b>\n"
            f"<b>ғσʀ ᴛєʟєɢʀᴧϻ ɢʀσᴜᴘꜱ & ᴄʜᴧηηєʟꜱ</b>\n\n"
            f"<b>🔥 ɪηꜱᴛᴧηᴛ ꜱᴛʀєᴧϻɪηɢ</b>\n"
            f"<b>❤️ ꜱϻσσᴛʜ ᴘʟᴧʏʙᴧᴄᴋ</b>\n"
            f"<b>🎧 ᴄʀʏꜱᴛᴧʟ ꜱσᴜηᴅ | ησ ʟᴧɢ</b>"
            f"</blockquote>\n\n"
            f"<b>Cʟɪᴄᴋ ᴏɴ ᴛʜᴇ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ɢᴇᴛ ɪɴғᴏʀᴍᴀᴛɪᴏɴ ᴀʙᴏᴜᴛ ᴍʏ ᴍᴏᴅᴜʟᴇs ᴀɴᴅ ᴄᴏᴍᴍᴀɴᴅs.</b>"
        )

    # 📸 SMART PHOTO LOGIC
    photo = None
    start_img = random.choice(raw_img.split("|||")) if raw_img else None
    
    if start_img:
        photo = start_img
    else:
        try:
            async for p in client.get_chat_photos(CallbackQuery.from_user.id, limit=1):
                photo = p.file_id
                break
        except:
            pass
            
        if not photo:
            photo = random.choice([
                "https://n.uguu.se/GvQQwulv.jpg",
                "https://d.uguu.se/nVKJFsNv.jpg",
                "https://n.uguu.se/CSSeXVzQ.jpg",
                "https://d.uguu.se/pBwORuAH.jpg"
            ])

    start_video = random.choice(raw_video.split("|||")) if raw_video else None
    effect_id = random.choice(raw_effect.split("|||")) if raw_effect else None

    try:
        if start_video:
            await CallbackQuery.edit_message_media(media=InputMediaVideo(media=start_video, caption=caption), reply_markup=markup)
        else:
            await CallbackQuery.edit_message_media(media=InputMediaPhoto(media=photo, caption=caption), reply_markup=markup)
    except Exception as e:
        try:
            await CallbackQuery.message.delete()
        except:
            pass
            
        send_kwargs = {
            "caption": caption,
            "reply_markup": markup,
            "has_spoiler": True,
            "parse_mode": ParseMode.HTML
        }
        if effect_id:
            send_kwargs["effect_id"] = effect_id
            
        if start_video:
            await CallbackQuery.message.reply_video(start_video, **send_kwargs)
        else:
            await CallbackQuery.message.reply_photo(photo, **send_kwargs)

# =====================================================================
# MANAGEMENT & SETTINGS
# =====================================================================

@Client.on_message(filters.command(["transfer", "transferowner"]) & ~BANNED_USERS)
async def transfer_owner(client, message):
    bot_id = (await client.get_me()).id
    user = message.from_user

    current_owner_id = await get_owner_id_from_db(bot_id)
    if user.id not in [OWNER_ID, current_owner_id]:
        return await message.reply_text("<tg-emoji emoji-id='6271611232457855630'>❌</tg-emoji> **Access Denied:** Only the Bot Owner can transfer ownership.")

    new_owner = None
    if message.reply_to_message:
        new_owner = message.reply_to_message.from_user
    elif len(message.command) > 1:
        try:
            new_owner = await client.get_users(message.command[1])
        except:
            return await message.reply_text("<tg-emoji emoji-id='6271611232457855630'>❌</tg-emoji> User not found! Check Username or ID.")
    else:
        return await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> **Usage:**\nReply to a user or type `/transfer @username`.")

    if new_owner.is_bot:
        return await message.reply_text("<tg-emoji emoji-id='6271611232457855630'>❌</tg-emoji> You cannot make a bot the owner.")
    if new_owner.id == user.id:
        return await message.reply_text("<tg-emoji emoji-id='6102938383456146362'>⚠️</tg-emoji> You are already the owner.")

    await clonebotdb.update_one({"bot_id": bot_id}, {"$set": {"user_id": new_owner.id}})
    await cloneownerdb.update_one({"bot_id": bot_id}, {"$set": {"user_id": new_owner.id}}, upsert=True)

    await message.reply_text(f"<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> **Ownership Transferred!**\n<tg-emoji emoji-id='6237864166879663987'>👑</tg-emoji> New Owner: {new_owner.mention}")

@Client.on_message(filters.command("viewstartsettings") & ~BANNED_USERS)
async def view_start_settings(client, message):
    bot_id = (await client.get_me()).id
    pos = await get_start_btn_pos(bot_id)
    await message.reply_text(f"<tg-emoji emoji-id='5350396951407895212'>⚙️</tg-emoji> **Settings Viewed**\nButton Position: `{pos}`")

@Client.on_message(filters.command("resetstartsetting") & ~BANNED_USERS)
async def reset_start_settings(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {
        "start_image": "", "start_video": "", "start_sticker": "", 
        "start_animation": "", "start_caption": "", "start_button": "", 
        "start_btn_pos": "", "start_reaction": "", "start_effect": ""
    }})
    await message.reply_text("<tg-emoji emoji-id='5373310679241466020'>🔄</tg-emoji> All Start Settings Reset!")

# =====================================================================
# START REACTION & EFFECT SETTERS
# =====================================================================

@Client.on_message(filters.command(["setstartreaction", "addstartreaction"]) & ~BANNED_USERS)
async def set_start_reaction_cmd(client, message):
    bot_id = (await client.get_me()).id
    if len(message.command) < 2:
        return await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> **Usage:** `/setstartreaction 🔥`\nYou can add multiple.")
    
    emoji = message.command[1]
    await add_start_content(bot_id, "start_reaction", emoji)
    await message.reply_text(f"<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Reaction Added: {emoji}")

@Client.on_message(filters.command(["delstartreaction", "resetstartreaction"]) & ~BANNED_USERS)
async def del_start_reaction_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_reaction": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Reaction Deleted (Default Random will be used)!")

@Client.on_message(filters.command(["setstarteffect", "addstarteffect"]) & ~BANNED_USERS)
async def set_start_effect_cmd(client, message):
    bot_id = (await client.get_me()).id
    if len(message.command) < 2:
        return await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> **Usage:** `/setstarteffect 🔥` or ID\n\nSupported: 🔥, 👍, 👎, ❤️, 🎉, 💩")
    
    EFFECT_MAP = {
        "🔥": "5104841245755180586",
        "👍": "5107584321108051014",
        "👎": "5104858069142078462",
        "❤️": "5044134455711629726",
        "🎉": "5046509860389126442",
        "💩": "5046589136895476101"
    }
    
    arg = message.command[1]
    effect_id = EFFECT_MAP.get(arg, arg)
    
    await add_start_content(bot_id, "start_effect", effect_id)
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Effect Added!")

@Client.on_message(filters.command(["delstarteffect", "resetstarteffect"]) & ~BANNED_USERS)
async def del_start_effect_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_effect": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Effect Deleted (Default Random will be used)!")

# =====================================================================
# MEDIA SETTERS
# =====================================================================

@Client.on_message(filters.command(["setstartimg", "addstartimg"]) & ~BANNED_USERS)
async def set_start_image_cmd(client, message):
    bot_id = (await client.get_me()).id
    if message.reply_to_message and message.reply_to_message.photo:
        await add_start_content(bot_id, "start_image", message.reply_to_message.photo.file_id)
        await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Image Added to Random List!")
    else:
        await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> Reply to a photo.")

@Client.on_message(filters.command(["delstartimg", "resetstartimg"]) & ~BANNED_USERS)
async def del_start_image_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_image": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Images Deleted!")

@Client.on_message(filters.command(["setstartvideo", "addstartvideo"]) & ~BANNED_USERS)
async def set_start_video_cmd(client, message):
    bot_id = (await client.get_me()).id
    if message.reply_to_message and message.reply_to_message.video:
        await add_start_content(bot_id, "start_video", message.reply_to_message.video.file_id)
        await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Video Added to Random List!")
    else:
        await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> Reply to a video.")

@Client.on_message(filters.command(["delstartvideo", "resetstartvideo"]) & ~BANNED_USERS)
async def del_start_video_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_video": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Start Videos Deleted!")

@Client.on_message(filters.command(["setstartsticker", "addstartsticker"]) & ~BANNED_USERS)
async def set_start_sticker_cmd(client, message):
    bot_id = (await client.get_me()).id
    if message.reply_to_message and message.reply_to_message.sticker:
        await add_start_content(bot_id, "start_sticker", message.reply_to_message.sticker.file_id)
        await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Sticker Added to Random List!")
    else:
        await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> Reply to a sticker.")

@Client.on_message(filters.command(["delstartsticker", "resetstartsticker"]) & ~BANNED_USERS)
async def del_start_sticker_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_sticker": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Stickers Deleted!")

@Client.on_message(filters.command(["setstartanimation", "addstartanimation"]) & ~BANNED_USERS)
async def set_start_animation_cmd(client, message):
    bot_id = (await client.get_me()).id
    if message.reply_to_message and message.reply_to_message.animation:
        await add_start_content(bot_id, "start_animation", message.reply_to_message.animation.file_id)
        await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Animation Added to Random List!")
    else:
        await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> Reply to a GIF.")

@Client.on_message(filters.command(["delstartanimation", "resetstartanimation"]) & ~BANNED_USERS)
async def del_start_animation_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_animation": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Animations Deleted!")

# =====================================================================
# CAPTION & BUTTON
# =====================================================================

@Client.on_message(filters.command(["setstartcaption", "addstartcaption"]) & ~BANNED_USERS)
async def set_start_caption_cmd(client, message):
    bot_id = (await client.get_me()).id
    if message.reply_to_message:
        text = message.reply_to_message.text.html if message.reply_to_message.text else message.reply_to_message.caption.html
        await add_start_content(bot_id, "start_caption", text)
        await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Caption Added to Random List!")
    else:
        await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> Reply to a text to add as Caption.")

@Client.on_message(filters.command(["delstartcaption", "resetstartcaption"]) & ~BANNED_USERS)
async def del_start_caption_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_caption": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Captions Deleted!")

@Client.on_message(filters.command(["setstartbutton", "addstartbutton"]) & ~BANNED_USERS)
async def set_start_button_cmd(client, message):
    bot_id = (await client.get_me()).id
    data = message.text.split(None, 1)[1] if len(message.command) > 1 else None
    
    if not data or "-" not in data: 
        return await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> Format: `/addstartbutton Text - URL`")
    
    txt, url = data.split("-", 1)
    btn_str = f"{txt.strip()} - {url.strip()}"
    
    await add_start_content(bot_id, "start_button", btn_str)
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Button Added to Random List!")

@Client.on_message(filters.command(["delstartbutton", "resetstartbutton"]) & ~BANNED_USERS)
async def del_start_button_cmd(client, message):
    bot_id = (await client.get_me()).id
    await clonebotdb.update_one({"bot_id": bot_id}, {"$unset": {"start_button": ""}})
    await message.reply_text("<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Custom Buttons Deleted!")

@Client.on_message(filters.command("setbtnpos") & ~BANNED_USERS)
async def set_btn_pos_cmd(client, message):
    bot_id = (await client.get_me()).id
    if len(message.command) < 2:
        return await message.reply_text("<tg-emoji emoji-id='5767288287001580715'>💡</tg-emoji> Usage: `/setbtnpos [UP/DOWN/MID]`")
    
    raw_pos = message.command[1].upper()
    valid_pos = ["UP", "TOP", "DOWN", "BOTTOM", "MID", "MIDDLE", "LEFT", "RIGHT"]
    
    if raw_pos in valid_pos:
        if raw_pos == "TOP": raw_pos = "UP"
        if raw_pos == "BOTTOM": raw_pos = "DOWN"
        if raw_pos == "MIDDLE": raw_pos = "MID"
        
        await clonebotdb.update_one({"bot_id": bot_id}, {"$set": {"start_btn_pos": raw_pos}}, upsert=True)
        await message.reply_text(f"<tg-emoji emoji-id='6280269890821558384'>✅</tg-emoji> Button Position: **{raw_pos}**")
    else:
        await message.reply_text("<tg-emoji emoji-id='6271611232457855630'>❌</tg-emoji> Invalid! Use: UP, DOWN, MID")
