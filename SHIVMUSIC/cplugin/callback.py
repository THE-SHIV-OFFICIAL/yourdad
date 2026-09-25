import random
import asyncio
from ftmgram import filters, Client
from ftmgram.types import CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup
from ftmgram.enums import ButtonStyle 

import config
from SHIVMUSIC import app, YouTube
from SHIVMUSIC.core.call import ANJALI
from SHIVMUSIC.misc import SUDOERS, db
from SHIVMUSIC.utils.database import (
    get_active_chats, get_lang, get_upvote_count, is_active_chat,
    is_music_playing, is_nonadmin_chat, music_off, music_on, set_loop, get_assistant,
    is_autoplay_on, autoplay_on, autoplay_off
)
from SHIVMUSIC.utils.decorators.language import languageCB
from SHIVMUSIC.utils.formatters import seconds_to_min
from SHIVMUSIC.utils.inline import close_markup
from SHIVMUSIC.cplugin.buttons import (
    stream_markup,
    stream_markup_timer,
    stream_markup2,
    stream_markup_timer2,
    panel_markup_clone,
)
from SHIVMUSIC.utils.stream.autoclear import auto_clean
from SHIVMUSIC.utils.thumbnails import get_thumb
from SHIVMUSIC.utils.player_ui import attach_player_rich_message
from config import BANNED_USERS, STREAM_IMG_URL, PLAYLIST_IMG_URL, votemode, adminlist
from strings import get_string
from SHIVMUSIC.utils.inline.start import private_panel
from SHIVMUSIC.cplugin.utils.decorators.admins import is_clone_admin

from button import styled_button

checker = {}
upvoters = {}


async def refresh_player_controls(
    chat_id, _, fallback_message=None, bot_username=None
):
    """Refresh the clone player's compact row after a play/pause action."""
    playing = await is_music_playing(chat_id)
    current = db.get(chat_id, [{}])[0] if db.get(chat_id) else {}
    if current.get("markup", "stream") == "stream":
        buttons = panel_markup_clone(
            _, current.get("vidid", ""), chat_id,
            playing=playing,
            bot_username=bot_username,
        )
    else:
        buttons = stream_markup2(_, chat_id, playing=playing)
    player_message = None
    try:
        player_message = db.get(chat_id, [{}])[0].get("mystic")
    except (IndexError, AttributeError, TypeError):
        pass
    player_message = player_message or fallback_message
    if not player_message:
        return
    try:
        await player_message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except Exception:
        if fallback_message and fallback_message is not player_message:
            try:
                await fallback_message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception:
                pass

def get_random_img(img_list):
    if img_list:
        return random.choice(img_list) if isinstance(img_list, list) else img_list
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg"

@Client.on_callback_query(filters.regex("settingsback_helper") & ~BANNED_USERS)
@languageCB
async def settings_back_helper(client: Client, CallbackQuery, _):
    await CallbackQuery.answer()
    img = get_random_img(config.START_IMG_URL)
    await CallbackQuery.edit_message_media(
        media=InputMediaPhoto(media=img, caption=_["start_2"].format(CallbackQuery.from_user.mention, app.mention)),
        reply_markup=InlineKeyboardMarkup(private_panel(_))
    )

@Client.on_callback_query(filters.regex("ADMIN") & ~BANNED_USERS)
@languageCB
async def del_back_playlist(client: Client, CallbackQuery, _):
    bot = await client.get_me()
    callback_data = CallbackQuery.data.strip()
    callback_request = callback_data.split(None, 1)[1]
    command, chat = callback_request.split("|")

    if "_" in str(chat):
        bet = chat.split("_")
        chat, counter = bet[0], bet[1]

    chat_id = int(chat)
    if not await is_active_chat(chat_id):
        return await CallbackQuery.answer(_["general_5"], show_alert=True)

    mention = CallbackQuery.from_user.mention
    user_id = CallbackQuery.from_user.id
    user_name = CallbackQuery.from_user.first_name

    is_non_admin = await is_nonadmin_chat(chat_id)
    if not is_non_admin:
        is_clone_auth = await is_clone_admin(bot.id, CallbackQuery.from_user.id)
        if CallbackQuery.from_user.id not in SUDOERS and not is_clone_auth:
            admins = adminlist.get(chat_id)
            if not admins or CallbackQuery.from_user.id not in admins:
                return await CallbackQuery.answer(_["admin_14"], show_alert=True)

    if command == "UpVote":
        if chat_id not in votemode: votemode[chat_id] = {}
        if chat_id not in upvoters: upvoters[chat_id] = {}

        voters = (upvoters[chat_id]).get(CallbackQuery.message.id, [])
        if CallbackQuery.from_user.id in voters:
            voters.remove(CallbackQuery.from_user.id)
            votemode[chat_id][CallbackQuery.message.id] = max(0, votemode[chat_id].get(CallbackQuery.message.id, 1) - 1)
        else:
            voters.append(CallbackQuery.from_user.id)
            votemode[chat_id][CallbackQuery.message.id] = votemode[chat_id].get(CallbackQuery.message.id, 0) + 1

        upvote = await get_upvote_count(chat_id)
        get_upvotes = votemode[chat_id][CallbackQuery.message.id]

        if get_upvotes >= upvote:
            await CallbackQuery.edit_message_text(_["admin_37"].format(upvote))
        else:
            upl = InlineKeyboardMarkup([[styled_button(text=f"🔥 {get_upvotes}", callback_data=f"ADMIN UpVote|{chat_id}_{counter}", style=ButtonStyle.PRIMARY)]])
            await CallbackQuery.answer(_["admin_40"], show_alert=True)
            await CallbackQuery.edit_message_reply_markup(reply_markup=upl)

    elif command == "Toggle":
        currently_playing = await is_music_playing(chat_id)
        if currently_playing:
            changed = await ANJALI.pause_stream(chat_id)
            if not changed:
                return await CallbackQuery.answer("⚠️ Pause failed. Check the voice chat.", show_alert=True)
            await music_off(chat_id)
            await CallbackQuery.answer("⏸ Paused")
        else:
            changed = await ANJALI.resume_stream(chat_id)
            if not changed:
                return await CallbackQuery.answer("⚠️ Resume failed. Check the voice chat.", show_alert=True)
            await music_on(chat_id)
            await CallbackQuery.answer("▶️ Playing")
        await refresh_player_controls(
            chat_id,
            _,
            CallbackQuery.message,
            getattr(getattr(client, "me", None), "username", None),
        )
    elif command == "Pause":
        if not await is_music_playing(chat_id): return await CallbackQuery.answer(_["admin_1"], show_alert=True)
        await CallbackQuery.answer()
        await ANJALI.pause_stream(chat_id)
        await music_off(chat_id)
        await refresh_player_controls(
            chat_id,
            _,
            CallbackQuery.message,
            getattr(getattr(client, "me", None), "username", None),
        )
        buttons = [[styled_button("ʀᴇsᴜᴍᴇ ▷", callback_data=f"ADMIN Resume|{chat_id}", style=ButtonStyle.SUCCESS), styled_button("ʀᴇᴘʟᴀʏ ↺", callback_data=f"ADMIN Replay|{chat_id}", style=ButtonStyle.PRIMARY)]]
        await CallbackQuery.message.reply_photo(photo=get_random_img(PLAYLIST_IMG_URL), caption=_["admin_2"].format(mention), reply_markup=InlineKeyboardMarkup(buttons))

    elif command == "Resume":
        if await is_music_playing(chat_id): return await CallbackQuery.answer(_["admin_3"], show_alert=True)
        await CallbackQuery.answer()
        await ANJALI.resume_stream(chat_id)
        await music_on(chat_id)
        await refresh_player_controls(
            chat_id,
            _,
            CallbackQuery.message,
            getattr(getattr(client, "me", None), "username", None),
        )
        buttons = [[styled_button("sᴋɪᴘ ‣‣I", callback_data=f"ADMIN Skip|{chat_id}", style=ButtonStyle.PRIMARY), styled_button("sᴛᴏᴘ ▢", callback_data=f"ADMIN Stop|{chat_id}", style=ButtonStyle.DANGER)], [styled_button("ᴘᴀᴜsᴇ II", callback_data=f"ADMIN Pause|{chat_id}", style=ButtonStyle.SECONDARY)]]
        await CallbackQuery.message.reply_photo(photo=get_random_img(PLAYLIST_IMG_URL), caption=_["admin_4"].format(mention), reply_markup=InlineKeyboardMarkup(buttons))

    elif command in ["Stop", "End"]:
        await CallbackQuery.answer()
        await ANJALI.stop_stream(chat_id)
        await set_loop(chat_id, 0)
        await CallbackQuery.message.reply_photo(photo=get_random_img(PLAYLIST_IMG_URL), caption=_["admin_5"].format(mention), reply_markup=close_markup(_))
        try: await CallbackQuery.message.delete()
        except: pass

    elif command == "Autoplay":
        state = await is_autoplay_on(chat_id)
        if state:
            await autoplay_off(chat_id)
            await CallbackQuery.answer("🔴 Ʌυᴛσᴘʟᴧʏ ᴅɪsᴧʙʟєᴅ!", show_alert=True)
            await CallbackQuery.message.reply_text(
                f"<blockquote><b><tg-emoji emoji-id=\"5318840353510408444\">🔴</tg-emoji> <tg-emoji emoji-id=\"6082387600599944892\">🎧</tg-emoji> Ʌυᴛσᴘʟᴧʏ sʏsᴛєϻ</b>\n\n<b>Ʌυᴛσᴘʟᴧʏ ғσʀ ᴛʜɪs ɢʀσυᴘ ɪs ησᴡ ᴅɪsᴧʙʟєᴅ <tg-emoji emoji-id=\"5318840353510408444\">🔴</tg-emoji>.</b>\n└ <b>ʙʏ :</b> {mention}</blockquote>",
                reply_markup=close_markup(_)
            )
        else:
            await autoplay_on(chat_id)
            await CallbackQuery.answer("🟢 Ʌυᴛσᴘʟᴧʏ єηᴧʙʟєᴅ!", show_alert=True)
            await CallbackQuery.message.reply_text(
                f"<blockquote><b><tg-emoji emoji-id=\"6113685078825505075\">🟢</tg-emoji> <tg-emoji emoji-id=\"6082387600599944892\">🎧</tg-emoji> Ʌυᴛσᴘʟᴧʏ sʏsᴛєϻ</b>\n\n<b>Ʌυᴛσᴘʟᴧʏ ғσʀ ᴛʜɪs ɢʀσυᴘ ɪs ησᴡ єηᴧʙʟєᴅ <tg-emoji emoji-id=\"6113685078825505075\">🟢</tg-emoji>.</b>\n└ <b>ʙʏ :</b> {mention}</blockquote>",
                reply_markup=close_markup(_)
            )

    elif command in ["Skip", "Replay"]:
        check = db.get(chat_id)
        if not check: return await CallbackQuery.answer("⚠️ Queue khali hai!", show_alert=True)

        await CallbackQuery.answer()

        if command == "Skip":
            popped = check.pop(0)
            if popped: await auto_clean(popped)
            if not check:
                await CallbackQuery.message.reply_text(_["admin_6"].format(mention, CallbackQuery.message.chat.title), reply_markup=close_markup(_))
                return await ANJALI.stop_stream(chat_id)

            clients = await ANJALI.get_active_clients(chat_id)
            pytgcalls_client = clients[0] if clients else ANJALI.one
            await ANJALI.change_stream(pytgcalls_client, chat_id)
            return await CallbackQuery.edit_message_text(f"<blockquote><b><tg-emoji emoji-id=\"5850346984501680054\">▶️</tg-emoji> ➻ sᴛʀєᴧϻ sᴋɪᴘᴘєᴅ <tg-emoji emoji-id=\"6172273586703700991\">🥀</tg-emoji></b>\n│ \n└<b>ʙʏ :</b> {mention}</blockquote>", reply_markup=close_markup(_))

        else:
            db[chat_id][0]["played"] = 0
            img = await get_thumb(check[0]["vidid"], user_id, user_name) or get_random_img(PLAYLIST_IMG_URL)
            await ANJALI.skip_stream(chat_id, check[0]["file"], video=True if check[0]["streamtype"]=="video" else False)

            run = await CallbackQuery.message.reply_photo(
                photo=img,
                caption=_["stream_1"].format(f"https://t.me/{app.username}?start=info_{check[0]['vidid']}", check[0]['title'][:23], check[0]['dur'], check[0]['by']),
                reply_markup=InlineKeyboardMarkup(stream_markup(_, chat_id))
            )
            await attach_player_rich_message(
                client,
                run,
                title=check[0]["title"],
                duration=check[0]["dur"],
                requested_by=check[0]["by"],
            )
            if chat_id in db and db[chat_id]:
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
            await CallbackQuery.edit_message_text(f"<blockquote><b><tg-emoji emoji-id=\"5960671702059848143\">⬅️</tg-emoji> ➻ sᴛʀєᴧϻ ʀє-ᴘʟᴧʏєᴅ <tg-emoji emoji-id=\"6172273586703700991\">🥀</tg-emoji></b>\n│ \n└<b>ʙʏ :</b> {mention}</blockquote>", reply_markup=close_markup(_))

async def markup_timer():
    while True:
        await asyncio.sleep(300)
        active_chats = await get_active_chats()
        for chat_id in active_chats:
            try:
                if not await is_music_playing(chat_id): continue
                playing = db.get(chat_id)
                if not playing or int(playing[0].get("seconds", 0)) == 0: continue
                mystic = playing[0].get("mystic")
                if not mystic: continue

                try: language = await get_lang(chat_id); _ = get_string(language)
                except: _ = get_string("en")

                markup = playing[0].get("markup", "stream")
                buttons = stream_markup_timer(_, chat_id, seconds_to_min(playing[0]["played"]), playing[0]["dur"]) if markup == "stream" else stream_markup_timer2(_, chat_id, seconds_to_min(playing[0]["played"]), playing[0]["dur"])
                await mystic.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
            except: continue

asyncio.create_task(markup_timer())


@Client.on_callback_query(filters.regex(r"^clone_unban_assistant"))
async def clone_unban_assistant(client: Client, callback: CallbackQuery):
    chat_id = callback.message.chat.id
    try:
        ub_id = int(callback.data.split("|", 1)[1])
    except Exception:
        ub = getattr(client, "assistant", None)
        if not ub:
            return await callback.answer("No assistant is connected to this bot.", show_alert=True)
        ub_id = ub.id if getattr(ub, "id", None) else (await ub.get_me()).id
    try:
        member = await client.get_chat_member(chat_id, callback.from_user.id)
        if member.status.name not in ("OWNER", "ADMINISTRATOR") and callback.from_user.id not in SUDOERS:
            return await callback.answer("Only chat admins can unban the assistant.", show_alert=True)
    except Exception:
        pass
    try:
        await client.unban_chat_member(chat_id, ub_id)
        await callback.answer("✅ Assistant unbanned successfully! Now play again.", show_alert=True)
        try:
            await callback.message.edit_text(
                "<blockquote><b><tg-emoji emoji-id=\"5409320020058584473\">🔓</tg-emoji> Assistant has been unbanned.</b>\n"
                f"<b>Unbanned by :</b> {callback.from_user.mention}\n<b>Use /play again to start the music.</b></blockquote>"
            )
        except Exception:
            pass
    except Exception:
        await callback.answer("❌ Couldn't unban the assistant. Please give me Ban Users admin permission.", show_alert=True)
