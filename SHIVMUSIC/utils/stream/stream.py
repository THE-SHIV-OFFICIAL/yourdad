import os
import random
import asyncio
import logging
from typing import Union

from ftmgram.types import InlineKeyboardMarkup

import config
from SHIVMUSIC import Carbon, YouTube, app
from SHIVMUSIC.core.call import ANJALI
from SHIVMUSIC.misc import db
from SHIVMUSIC.utils.database import add_active_video_chat, is_active_chat
from SHIVMUSIC.utils.exceptions import AssistantErr
from SHIVMUSIC.utils.inline import aq_markup, close_markup, stream_markup
from SHIVMUSIC.utils.stream.queue import put_queue, put_queue_index
from SHIVMUSIC.utils.pastebin import ANJALIBin
from SHIVMUSIC.utils.thumbnails import get_thumb 
from SHIVMUSIC.utils.player_ui import attach_player_rich_message

LOGGER = logging.getLogger(__name__)

def get_random_img(img_list):
    if img_list:
        if isinstance(img_list, list):
            return random.choice(img_list)
        return img_list
    return "https://files.catbox.moe/6r97s4.jpg"

# ⚡ SPEED OPTIMIZATION: Background Delete Task
async def safe_delete(message):
    if not message: return
    try: await message.delete()
    except: pass

# 🛡️ BULLETPROOF CARD SENDER: Photo fail hone par Text send karega
async def safe_send_card(
    chat_id,
    photo_url,
    caption,
    reply_markup,
    *,
    title=None,
    duration=None,
    requested_by=None,
    playing=True,
):
    run = None
    try:
        if not photo_url:
            photo_url = get_random_img(config.PLAYLIST_IMG_URL)
        elif isinstance(photo_url, list):
            photo_url = random.choice(photo_url)
            
        run = await app.send_photo(chat_id, photo=photo_url, caption=caption, reply_markup=reply_markup)
    except Exception as e:
        LOGGER.error(f"Image Send Failed: {e}. Falling back to text message.")
        try:
            # Agar photo fail hui toh sirf text aur buttons bhej do
            run = await app.send_message(chat_id, text=caption, reply_markup=reply_markup, disable_web_page_preview=True)
        except Exception as ex:
            LOGGER.error(f"Text send also failed: {ex}")
            return None
    if run and title is not None:
        await attach_player_rich_message(
            app,
            run,
            title=title,
            duration=duration,
            requested_by=requested_by,
            playing=playing,
        )
    return run

async def stream(
    _, mystic, user_id, result, chat_id, user_name, original_chat_id,
    video: Union[bool, str] = None, streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None, forceplay: Union[bool, str] = None,
):
    if not result: return
    if forceplay: await ANJALI.force_stop_stream(chat_id)

    if streamtype == "playlist":
        msg = f"{_['play_19']}\n\n"
        count = 0
        for search in result:
            if int(count) == config.PLAYLIST_FETCH_LIMIT: continue
            try:
                title, duration_min, duration_sec, thumbnail, vidid = await YouTube.details(search, False if spotify else True)
            except: continue
            if str(duration_min) == "None" or duration_sec > config.DURATION_LIMIT: continue
            
            if await is_active_chat(chat_id):
                await put_queue(chat_id, original_chat_id, f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio")
                position = len(db.get(chat_id)) - 1
                count += 1
                msg += f"{count}. {title[:70]}\n{_['play_20']} {position}\n\n"
            else:
                if not forceplay: db[chat_id] = []
                status = True if video else None
                file_path, direct = await YouTube.download(vidid, mystic, video=status, videoid=True)
                if not file_path or str(file_path) == "None": raise AssistantErr(_["play_14"])
                
                asyncio.create_task(safe_delete(mystic))
                
                await ANJALI.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
                await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
                
                img = await get_thumb(vidid, user_id, app)
                if not img: img = get_random_img(config.PLAYLIST_IMG_URL)
                
                caption_text = _["stream_1"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name)
                markup = InlineKeyboardMarkup(stream_markup(_, chat_id))
                
                run = await safe_send_card(
                    original_chat_id, img, caption_text, markup,
                    title=title, duration=duration_min, requested_by=user_name,
                )
                if run and db.get(chat_id) and isinstance(db[chat_id], list) and len(db[chat_id]) > 0:
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"
                    
        if count == 0: return
        else:
            asyncio.create_task(safe_delete(mystic))
            link = await ANJALIBin(msg)
            carbon = await Carbon.generate(msg, random.randint(100, 10000000))
            return await app.send_photo(original_chat_id, photo=carbon, caption=_["play_21"].format(position, link), reply_markup=close_markup(_), has_spoiler=False)

    elif streamtype == "youtube":
        link, vidid, title, duration_min, thumbnail = result["link"], result["vidid"], (result["title"]).title(), result["duration_min"], result["thumb"]
        status = True if video else None
        file_path, direct = await YouTube.download(vidid, mystic, videoid=True, video=status)
        if not file_path or str(file_path) == "None": raise AssistantErr(_["play_14"])
        
        asyncio.create_task(safe_delete(mystic))
        
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            await app.send_message(chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], duration_min, user_name), reply_markup=InlineKeyboardMarkup(aq_markup(_, chat_id)))
        else:
            if not forceplay: db[chat_id] = []
            await ANJALI.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
            await put_queue(chat_id, original_chat_id, file_path if direct else f"vid_{vidid}", title, duration_min, user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
            
            img = await get_thumb(vidid, user_id, app)
            if not img: img = get_random_img(config.PLAYLIST_IMG_URL)
            
            caption_text = _["stream_1"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], duration_min, user_name)
            markup = InlineKeyboardMarkup(stream_markup(_, chat_id))
            
            run = await safe_send_card(
                original_chat_id, img, caption_text, markup,
                title=title, duration=duration_min, requested_by=user_name,
            )
            if run and db.get(chat_id) and isinstance(db[chat_id], list) and len(db[chat_id]) > 0:
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"

    elif streamtype == "live":
        link, vidid, title, thumbnail = result["link"], result["vidid"], (result["title"]).title(), result["thumb"]
        status = True if video else None
        
        asyncio.create_task(safe_delete(mystic))
        
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, f"live_{vidid}", title, "Live", user_name, vidid, user_id, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            await app.send_message(chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], "Live", user_name), reply_markup=InlineKeyboardMarkup(aq_markup(_, chat_id)))
        else:
            if not forceplay: db[chat_id] = []
            n, file_path = await YouTube.video(link)
            if n == 0 or not file_path or str(file_path) == "None": raise AssistantErr(_["str_3"])
            await ANJALI.join_call(chat_id, original_chat_id, file_path, video=status, image=thumbnail)
            await put_queue(chat_id, original_chat_id, f"live_{vidid}", title, "Live", user_name, vidid, user_id, "video" if video else "audio", forceplay=forceplay)
            
            img = await get_thumb(vidid, user_id, app)
            if not img: img = get_random_img(config.PLAYLIST_IMG_URL)
            
            caption_text = _["stream_1"].format(f"https://t.me/{app.username}?start=info_{vidid}", title[:23], "Live", user_name)
            markup = InlineKeyboardMarkup(stream_markup(_, chat_id))
            
            run = await safe_send_card(
                original_chat_id, img, caption_text, markup,
                title=title, duration="Live", requested_by=user_name,
            )
            if run and db.get(chat_id) and isinstance(db[chat_id], list) and len(db[chat_id]) > 0:
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"

    elif streamtype == "soundcloud":
        file_path, title, duration_min = result["filepath"], result["title"], result["duration_min"]
        
        asyncio.create_task(safe_delete(mystic))
        
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "audio")
            position = len(db.get(chat_id)) - 1
            await app.send_message(chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], duration_min, user_name), reply_markup=InlineKeyboardMarkup(aq_markup(_, chat_id)))
        else:
            if not forceplay: db[chat_id] = []
            await ANJALI.join_call(chat_id, original_chat_id, file_path, video=None)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "audio", forceplay=forceplay)
            
            caption_text = _["stream_1"].format(config.SUPPORT_CHAT, title[:23], duration_min, user_name)
            markup = InlineKeyboardMarkup(stream_markup(_, chat_id))
            
            run = await safe_send_card(
                original_chat_id, config.SOUNCLOUD_IMG_URL, caption_text, markup,
                title=title, duration=duration_min, requested_by=user_name,
            )
            if run and db.get(chat_id) and isinstance(db[chat_id], list) and len(db[chat_id]) > 0:
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"

    elif streamtype == "telegram":
        file_path, link, title, duration_min = result["path"], result["link"], (result["title"]).title(), result["dur"]
        status = True if video else None
        
        asyncio.create_task(safe_delete(mystic))
        
        if await is_active_chat(chat_id):
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            await app.send_message(chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], duration_min, user_name), reply_markup=InlineKeyboardMarkup(aq_markup(_, chat_id)))
        else:
            if not forceplay: db[chat_id] = []
            await ANJALI.join_call(chat_id, original_chat_id, file_path, video=status)
            await put_queue(chat_id, original_chat_id, file_path, title, duration_min, user_name, streamtype, user_id, "video" if video else "audio", forceplay=forceplay)
            if video: await add_active_video_chat(chat_id)
            
            tg_img = config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL
            caption_text = _["stream_1"].format(link, title[:23], duration_min, user_name)
            markup = InlineKeyboardMarkup(stream_markup(_, chat_id))
            
            run = await safe_send_card(
                original_chat_id, tg_img, caption_text, markup,
                title=title, duration=duration_min, requested_by=user_name,
            )
            if run and db.get(chat_id) and isinstance(db[chat_id], list) and len(db[chat_id]) > 0:
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"

    elif streamtype == "index":
        link, title, duration_min = result, "Index or M3u8 Link", "00:00"
        
        asyncio.create_task(safe_delete(mystic))
        
        if await is_active_chat(chat_id):
            await put_queue_index(chat_id, original_chat_id, "index_url", title, duration_min, user_name, link, "video" if video else "audio")
            position = len(db.get(chat_id)) - 1
            await app.send_message(chat_id=original_chat_id, text=_["queue_4"].format(position, title[:27], duration_min, user_name), reply_markup=InlineKeyboardMarkup(aq_markup(_, chat_id)))
        else:
            if not forceplay: db[chat_id] = []
            await ANJALI.join_call(chat_id, original_chat_id, link, video=True if video else None)
            await put_queue_index(chat_id, original_chat_id, "index_url", title, duration_min, user_name, link, "video" if video else "audio", forceplay=forceplay)
            
            caption_text = _["stream_2"].format(user_name)
            markup = InlineKeyboardMarkup(stream_markup(_, chat_id))
            
            run = await safe_send_card(
                original_chat_id, config.STREAM_IMG_URL, caption_text, markup,
                title=title, duration=duration_min, requested_by=user_name,
            )
            if run and db.get(chat_id) and isinstance(db[chat_id], list) and len(db[chat_id]) > 0:
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
