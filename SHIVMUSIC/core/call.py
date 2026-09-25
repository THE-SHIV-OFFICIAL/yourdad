import asyncio
import os
import random
import logging
from datetime import datetime, timedelta
from typing import Union

from ftmgram import Client
from ftmgram.types import InlineKeyboardMarkup, InlineKeyboardButton
from ftmgram.enums import ParseMode

from pytgcalls import PyTgCalls
from pytgcalls.mtproto.bridged_client import BridgedClient
from pytgcalls.types import MediaStream, AudioQuality, VideoQuality

import config
from SHIVMUSIC import LOGGER, YouTube, app, userbot
from SHIVMUSIC.misc import db
from SHIVMUSIC.utils.database import (
    add_active_chat,
    add_active_video_chat,
    get_lang,
    get_loop,
    group_assistant,
    is_autoend,
    music_on,
    remove_active_chat,
    remove_active_video_chat,
    set_loop,
    is_autoplay_on,
)
from SHIVMUSIC.utils.autoplay import fetch_autoplay_track, remember_played
from SHIVMUSIC.utils.stream.queue import put_queue
from SHIVMUSIC.utils.logger import play_logs, autoplay_logs
from SHIVMUSIC.utils.exceptions import AssistantErr
from SHIVMUSIC.utils.formatters import check_duration, seconds_to_min, speed_converter
from SHIVMUSIC.utils.inline.play import stream_markup, telegram_markup
from SHIVMUSIC.utils.stream.autoclear import auto_clean
from strings import get_string
from SHIVMUSIC.utils.thumbnails import get_thumb
from SHIVMUSIC.utils.player_ui import attach_player_rich_message
from SHIVMUSIC.cplugin.buttons import panel_markup_clone
from SHIVMUSIC.error_logger import report_exception


def _alias_pyrogram_to_ftmgram():
    """PyTgCalls imports `pyrogram.*`; map it to ftmgram when pyrogram is absent."""
    import importlib
    import importlib.abc
    import importlib.util
    import sys

    if getattr(sys, "_shiv_pyrogram_alias", False):
        return
    sys._shiv_pyrogram_alias = True
    class _Loader(importlib.abc.Loader):
        def __init__(self, real):
            self.real = real

        def create_module(self, spec):
            return importlib.import_module(self.real)

        def exec_module(self, module):
            return None

    class _Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname != "pyrogram" and not fullname.startswith("pyrogram."):
                return None
            real = "ftmgram" + fullname[len("pyrogram"):]
            if importlib.util.find_spec(real) is None:
                return None
            return importlib.util.spec_from_loader(fullname, _Loader(real))

    for name in [n for n in sys.modules if n == "pyrogram" or n.startswith("pyrogram.")]:
        sys.modules.pop(name, None)
    sys.meta_path.insert(0, _Finder())


def _install_pytgcalls_client_compatibility():
    """Make PyTgCalls recognise our wrapped Pyrogram client.

    ErrorLoggingClient is a subclass of ftmgram.Client, but its direct class
    module is SHIVMUSIC.error_logger. Older/current PyTgCalls releases detect
    the MTProto library from only the direct class module and consequently
    raise InvalidMTProtoClient for this perfectly valid client.
    """
    _alias_pyrogram_to_ftmgram()
    original_package_name = BridgedClient.package_name

    def package_name(client):
        for client_class in type(client).__mro__:
            module = getattr(client_class, "__module__", "")
            root_module = module.split(".", 1)[0]
            if root_module in {"ftmgram", "pyrogram"}:
                # PyTgCalls only understands the name "pyrogram".
                return "pyrogram"
            if root_module == "telethon":
                return "telethon"
        return original_package_name(client)

    BridgedClient.package_name = staticmethod(package_name)


_install_pytgcalls_client_compatibility()


def handle_asyncio_exceptions(loop, context):
    msg = context.get("exception", context.get("message"))
    msg_str = str(msg).lower()

    expected_sync_events = [
        "groupcall_forbidden", 
        "setvideocallstatus", 
        "groupcall_invalid", 
        "no active group call", 
        "group call has already ended"
    ]

    if any(err in msg_str for err in expected_sync_events):
        logging.getLogger("asyncio").info(f"ℹ️ VC State Sync (Harmless): {msg}")
    else:
        logging.getLogger("asyncio").error(f"❌ Unhandled Asyncio Error: {msg}")

autoend = {}
counter = {}

FORCE_JOIN_LINKS = [
    "https://t.me/betabot_hub",
    "https://t.me/betabot_support",
    "https://t.me/sukoon_s",
]

def get_random_img(img_list):
    if img_list:
        if isinstance(img_list, list):
            return random.choice(img_list)
        return img_list
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg" 

async def _clear_(chat_id):
    db[chat_id] = []
    await remove_active_video_chat(chat_id)
    await remove_active_chat(chat_id)

class Call:
    def __init__(self):
        # Reuse the assistant clients that Userbot owns. Creating another
        # client for every session doubled Telegram connections and memory.
        self.userbot1 = userbot.one
        self.one = PyTgCalls(self.userbot1, cache_duration=100)

        self.two = None
        if getattr(config, "STRING2", None):
            self.userbot2 = userbot.two
            self.two = PyTgCalls(self.userbot2, cache_duration=100)

        self.three = None
        if getattr(config, "STRING3", None):
            self.userbot3 = userbot.three
            self.three = PyTgCalls(self.userbot3, cache_duration=100)

        self.four = None
        if getattr(config, "STRING4", None):
            self.userbot4 = userbot.four
            self.four = PyTgCalls(self.userbot4, cache_duration=100)

        self.five = None
        if getattr(config, "STRING5", None):
            self.userbot5 = getattr(userbot, "five", None)
            if self.userbot5:
                self.five = PyTgCalls(self.userbot5, cache_duration=100)

        self.custom_assistants = {} 
        self._stream_locks = {}
        self.active_clients = {} 
        self._started_calls = []
        self._setup_event_handlers()

    def _telegram_client_for_call(self, call_client):
        """Map a PyTgCalls instance back to its Telegram assistant client."""
        for call_instance, telegram_client in (
            (self.one, self.userbot1),
            (self.two, getattr(self, "userbot2", None)),
            (self.three, getattr(self, "userbot3", None)),
            (self.four, getattr(self, "userbot4", None)),
            (self.five, getattr(self, "userbot5", None)),
        ):
            if call_instance is call_client and telegram_client is not None:
                return telegram_client
        return self.userbot1

    def _setup_event_handlers(self):
        clients = [self.one, self.two, self.three, self.four, self.five]
        for client in clients:
            if not client:
                continue

            @client.on_update()
            async def stream_handler(c, update, call_instance=client):
                try:
                    c_id = getattr(update, "chat_id", None)
                    if not c_id: return

                    t_name = type(update).__name__
                    if "ChatUpdate" in t_name:
                        status = str(getattr(update, "status", "")).upper()
                        if "KICKED" in status or "LEFT" in status or "CLOSED" in status:
                            await self.stop_stream(c_id)
                    elif "StreamEnd" in t_name or "StreamAudioEnded" in t_name or "StreamVideoEnded" in t_name:
                        await self.change_stream(c, c_id)
                except Exception as exception:
                    await report_exception(
                        self._telegram_client_for_call(call_instance),
                        exception,
                        context="PyTgCalls stream update handler",
                        callback=stream_handler,
                        update=update,
                    )

    async def _safe_change_stream(self, client, chat_id, file_path, video=False, extra_args=""):
        if not video:
            stream = MediaStream(file_path, audio_parameters=AudioQuality.HIGH, ffmpeg_parameters=extra_args)
            await client.play(chat_id, stream)
            return

        try: 
            stream = MediaStream(
                file_path, 
                audio_parameters=AudioQuality.HIGH, 
                video_parameters=VideoQuality.HD_720p, 
                ffmpeg_parameters=extra_args
            )
            await client.play(chat_id, stream)
        except Exception as e:
            LOGGER(__name__).warning(f"720p Change Stream failed, auto-switching to 480p: {e}")
            stream = MediaStream(
                file_path, 
                audio_parameters=AudioQuality.HIGH, 
                video_parameters=VideoQuality.SD_480p, 
                ffmpeg_parameters=extra_args
            )
            await client.play(chat_id, stream)

    async def _safe_join_call(self, assistant_to_join, chat_id, file_path, video=False):
        if not video:
            stream = MediaStream(file_path, audio_parameters=AudioQuality.HIGH)
            return await assistant_to_join.play(chat_id, stream)

        try: 
            stream = MediaStream(
                file_path, 
                audio_parameters=AudioQuality.HIGH, 
                video_parameters=VideoQuality.HD_720p
            )
            await assistant_to_join.play(chat_id, stream)
        except Exception as e:
            LOGGER(__name__).warning(f"720p Join Call failed, auto-switching to 480p: {e}")
            stream = MediaStream(
                file_path, 
                audio_parameters=AudioQuality.HIGH, 
                video_parameters=VideoQuality.SD_480p
            )
            await assistant_to_join.play(chat_id, stream)

    async def get_active_clients(self, chat_id):
        try: chat_id = int(chat_id)
        except: pass
        clients = []
        if chat_id in self.active_clients:
            val = self.active_clients[chat_id]
            if isinstance(val, list):
                clients.extend(val)
            else:
                clients.append(val)
        if not clients:
            try:
                main_ass = await group_assistant(self, chat_id)
                clients.append(main_ass)
            except:
                clients.append(self.one)
        return list(set(clients))

    async def pause_stream(self, chat_id: int, assistant_type=None):
        try: chat_id = int(chat_id)
        except: pass
        assistants = await self.get_active_clients(chat_id)
        paused = False
        last_error = None
        for assistant in assistants:
            try:
                await assistant.pause_stream(chat_id)
                paused = True
            except Exception as e:
                last_error = e
                LOGGER(__name__).error(f"Pause error: {e}")
        if not paused and last_error:
            raise last_error
        return paused

    async def resume_stream(self, chat_id: int, assistant_type=None):
        try: chat_id = int(chat_id)
        except: pass
        assistants = await self.get_active_clients(chat_id)
        resumed = False
        last_error = None
        for assistant in assistants:
            try:
                await assistant.resume_stream(chat_id)
                resumed = True
            except Exception as e:
                last_error = e
                LOGGER(__name__).error(f"Resume error: {e}")
        if not resumed and last_error:
            raise last_error
        return resumed

    async def stop_stream(self, chat_id: int, assistant_type=None):
        try: chat_id = int(chat_id)
        except: pass

        try: await _clear_(chat_id)
        except: pass

        active_assistants = await self.get_active_clients(chat_id)
        for assistant in active_assistants:
            if assistant:
                try: 
                    await assistant.leave_call(chat_id)
                    LOGGER(__name__).info(f"✅ Assistant left VC successfully in chat {chat_id}.")
                except Exception as e: 
                    error_msg = str(e).lower()
                    ignore_list = ["no active group call", "already ended", "not in a call", "groupcall_forbidden", "groupcall_invalid"]
                    if any(ign in error_msg for ign in ignore_list):
                        LOGGER(__name__).info(f"ℹ️ Assistant State Sync: VC already closed in {chat_id}.")
                    else:
                        LOGGER(__name__).error(f"❌ Assistant failed to leave VC in {chat_id}: {e}")

        if chat_id in self.active_clients: 
            del self.active_clients[chat_id]

    async def stop_stream_force(self, chat_id: int):
        try: chat_id = int(chat_id)
        except: pass

        active_assistants = await self.get_active_clients(chat_id)
        for assistant in active_assistants:
            if assistant:
                try: 
                    await assistant.leave_call(chat_id)
                except Exception as e: 
                    error_msg = str(e).lower()
                    ignore_list = ["no active group call", "already ended", "not in a call", "groupcall_forbidden", "groupcall_invalid"]
                    if any(ign in error_msg for ign in ignore_list):
                        LOGGER(__name__).info(f"ℹ️ Assistant State Sync: VC already closed in {chat_id} (Force).")
                    else:
                        LOGGER(__name__).error(f"❌ Assistant force-leave failed in {chat_id}: {e}")

        if chat_id in self.active_clients: 
            del self.active_clients[chat_id]

        try: await _clear_(chat_id)
        except: pass

    async def force_stop_stream(self, chat_id: int):
        """Compatibility name used by the main and clone play handlers."""
        return await self.stop_stream_force(chat_id)

    async def speedup_stream(self, chat_id: int, file_path, speed, playing):
        try: chat_id = int(chat_id)
        except: pass
        assistants = await self.get_active_clients(chat_id)
        assistant = assistants[0] if assistants else self.one
        if str(speed) != str("1.0"):
            base = os.path.basename(file_path)
            chatdir = os.path.join(os.getcwd(), "playback", str(speed))
            if not os.path.isdir(chatdir):
                os.makedirs(chatdir)
            out = os.path.join(chatdir, base)
            if not os.path.isfile(out):
                if str(speed) == str("0.5"): vs = 2.0
                if str(speed) == str("0.75"): vs = 1.35
                if str(speed) == str("1.5"): vs = 0.68
                if str(speed) == str("2.0"): vs = 0.5
                proc = await asyncio.create_subprocess_shell(
                    cmd=(f"ffmpeg -i {file_path} -filter:v setpts={vs}*PTS -filter:a atempo={speed} {out}"),
                    stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
        else:
            out = file_path

        loop = asyncio.get_running_loop()

        dur = await loop.run_in_executor(None, check_duration, out)
        dur = int(dur)
        played, con_seconds = speed_converter(playing[0]["played"], speed)
        duration = seconds_to_min(dur)

        is_video = playing[0]["streamtype"] == "video"
        extra_args = f"-ss {played} -to {duration}"

        if str(db[chat_id][0]["file"]) == str(file_path):
            for assistant in assistants:
                try: await self._safe_change_stream(assistant, chat_id, out, is_video, extra_args)
                except: pass
        else: raise AssistantErr("Umm")

        if str(db[chat_id][0]["file"]) == str(file_path):
            exis = (playing[0]).get("old_dur")
            if not exis:
                db[chat_id][0]["old_dur"] = db[chat_id][0]["dur"]
                db[chat_id][0]["old_second"] = db[chat_id][0]["seconds"]
            db[chat_id][0]["played"] = con_seconds
            db[chat_id][0]["dur"] = duration
            db[chat_id][0]["seconds"] = dur
            db[chat_id][0]["speed_path"] = out
            db[chat_id][0]["speed"] = speed

    async def skip_stream(self, chat_id: int, link: str, video: Union[bool, str] = None, image: Union[bool, str] = None, assistant_type=None):
        try: chat_id = int(chat_id)
        except: pass
        assistants = await self.get_active_clients(chat_id)
        for assistant in assistants:
            try: await self._safe_change_stream(assistant, chat_id, link, video)
            except: pass

    async def seek_stream(self, chat_id, file_path, to_seek, duration, mode):
        try: chat_id = int(chat_id)
        except: pass
        assistants = await self.get_active_clients(chat_id)
        is_video = mode == "video"
        extra_args = f"-ss {to_seek} -to {duration}"
        for assistant in assistants:
            try: await self._safe_change_stream(assistant, chat_id, file_path, is_video, extra_args)
            except: pass

    async def autoplay_start(self, chat_id: int, original_chat_id: int, seed_title: str, seed_vidid: str = None, client: PyTgCalls = None, bot_client = None) -> bool:
        if seed_vidid:
            remember_played(chat_id, seed_vidid)

        chat_client = bot_client or app 
        
        status_msg = None
        try:
            status_msg = await chat_client.send_message(original_chat_id, "ʜσʟᴅ ση...\n\nᴅσᴡηʟσᴧᴅɪηɢ ηєxᴛ ϻєᴅɪᴧ ғʀσϻ ᴛʜє ǫυєυє.")
        except Exception:
            pass

        async def _fail() -> bool:
            if status_msg:
                try: await status_msg.delete()
                except: pass
            return False

        track = await fetch_autoplay_track(chat_id, seed_title, seed_vidid)
        if not track:
            return await _fail()

        try:
            language = await get_lang(chat_id)
            _ = get_string(language)
        except:
            _ = get_string("en")

        try:
            file_path, direct = await YouTube.download(track["vidid"], None, videoid=True)
        except Exception:
            return await _fail()

        if not file_path:
            return await _fail()

        remember_played(chat_id, track["vidid"])
        title = track["title"].title()
        duration_min = track["duration_min"]

        await put_queue(
            chat_id,
            original_chat_id,
            file_path if direct else f"vid_{track['vidid']}",
            title,
            duration_min,
            "🔁 ᴀᴜᴛᴏᴘʟᴀʏ",
            track["vidid"],
            1,
            "audio",
            forceplay=True,
        )

        if db.get(chat_id):
            db[chat_id][-1]["client"] = chat_client

        active_assistants = await self.get_active_clients(chat_id)
        assistant = client if client else (active_assistants[0] if active_assistants else self.one)

        try:
            await self._safe_change_stream(assistant, chat_id, file_path, video=False)
        except Exception:
            return await _fail()

        try:
            is_clone = (chat_client.me.id != app.me.id) if chat_client.me else False
            bot_username = chat_client.me.username if chat_client.me else app.username
        except:
            is_clone = False
            bot_username = app.username

        try:
            img = await get_thumb(track["vidid"], 0, chat_client) or get_random_img(config.PLAYLIST_IMG_URL)
            
            if is_clone:
                button = panel_markup_clone(
                    _, track["vidid"], chat_id, bot_username=bot_username
                )
            else:
                button = stream_markup(_, chat_id)
            
            run = await chat_client.send_photo(
                chat_id=original_chat_id,
                photo=img,
                caption=_["stream_1"].format(
                    f"https://t.me/{bot_username}?start=info_{track['vidid']}",
                    title[:23],
                    duration_min,
                    "ᴀᴜᴛᴏᴘʟᴀʏ 🎧",
                ),
                reply_markup=InlineKeyboardMarkup(button),
            )
            await attach_player_rich_message(
                chat_client,
                run,
                title=title,
                duration=duration_min,
                requested_by="ᴀᴜᴛᴏᴘʟᴀʏ 🎧",
            )
            if db.get(chat_id):
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "stream"
        except Exception as e:
            LOGGER(__name__).error(f"Autoplay Send Photo Error: {e}")
            pass

        if status_msg:
            try: await status_msg.delete()
            except Exception: pass

        try:
            upcoming = None
            queue_now = db.get(chat_id) or []
            if len(queue_now) > 1:
                upcoming = str(queue_now[1].get("title") or "").title() or None
            await autoplay_logs(chat_client, original_chat_id, title, upcoming)
        except Exception as exception:
            LOGGER(__name__).error(f"Autoplay logger failed: {exception}")

        try:
            from SHIVMUSIC.cplugin.setinfo import get_log_channel
            from SHIVMUSIC.utils.database.clonedb import get_owner_id_from_db
            
            c_bot_id = chat_client.me.id if chat_client.me else None
            if c_bot_id:
                logger_id = await get_log_channel(c_bot_id)
                
                if not logger_id or str(logger_id) == "-100":
                    logger_id = await get_owner_id_from_db(c_bot_id)
                
                if logger_id:
                    c_bot_name = chat_client.me.first_name if chat_client.me else chat_client.name
                    try:
                        chat_info = await chat_client.get_chat(original_chat_id)
                        chat_title = f"{chat_info.title} [`{original_chat_id}`]"
                    except:
                        chat_title = f"[`{original_chat_id}`]"

                    log_text = (
                        f"<blockquote><b>{c_bot_name} ᴘʟᴀʏ ʟᴏɢ</b>\n\n"
                        f"<b>• ʀᴇǫᴜᴇsᴛ ʙʏ :</b> ᴀᴜᴛᴏᴘʟᴀʏ 🎧\n"
                        f"<b>• ǫᴜᴇʀʏ :</b> {title}\n"
                        f"<b>• ᴄʜᴀᴛ :</b> {chat_title}\n"
                        f"<b>• ᴏᴡɴᴇʀ :</b> {logger_id}</blockquote>"
                    )
                    await chat_client.send_message(logger_id, log_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            LOGGER(__name__).error(f"Autoplay Log Error: {e}")
            pass

        return True

    async def join_call(self, chat_id: int, original_chat_id: int, link, video: Union[bool, str] = None, image: Union[bool, str] = None, userbot=None):
        assistant_to_join = None
        if userbot:
            if FORCE_JOIN_LINKS:
                for link_join in FORCE_JOIN_LINKS:
                    try:
                        await userbot.join_chat(link_join)
                        await asyncio.sleep(0.5) 
                    except: pass
            user_id = userbot.me.id
            if user_id in self.custom_assistants:
                assistant_to_join = self.custom_assistants[user_id]
            else:
                assistant_to_join = PyTgCalls(userbot, cache_duration=100)

                @assistant_to_join.on_update()
                async def clone_stream_handler(client, update):
                    try:
                        c_id = getattr(update, "chat_id", None)
                        if not c_id: return

                        t_name = type(update).__name__
                        if "ChatUpdate" in t_name:
                            status = str(getattr(update, "status", "")).upper()
                            if "KICKED" in status or "LEFT" in status or "CLOSED" in status:
                                await self.stop_stream(c_id)
                        elif "StreamEnd" in t_name or "StreamAudioEnded" in t_name or "StreamVideoEnded" in t_name:
                            await self.change_stream(client, c_id)
                    except Exception as e:
                        await report_exception(
                            userbot,
                            e,
                            context="Clone PyTgCalls stream update handler",
                            callback=clone_stream_handler,
                            update=update,
                        )

                await assistant_to_join.start()
                self.custom_assistants[user_id] = assistant_to_join
        else:
            assistant_to_join = await group_assistant(self, chat_id)

        candidates = []
        for candidate in [assistant_to_join, self.one, self.two, self.three, self.four, self.five]:
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        last_error = None
        for candidate in candidates:
            try:
                await self._safe_join_call(candidate, chat_id, link, video)
                assistant_to_join = candidate
                break
            except Exception as exc:
                last_error = exc
                LOGGER(__name__).warning(
                    "Assistant could not join VC %s; trying another assistant: %s",
                    chat_id,
                    exc,
                )
        else:
            # Don't leave a failed assistant cached. A later pause/skip/play
            # would otherwise keep targeting the client that already failed.
            self.active_clients.pop(chat_id, None)
            if last_error:
                await report_exception(
                    userbot or self.userbot1,
                    last_error,
                    context=f"All assistants failed to start playback in chat {chat_id}",
                )

            error_text = str(last_error or "Unknown playback error")
            error_name = type(last_error).__name__ if last_error else "UnknownError"
            error_key = f"{error_name} {error_text}".lower().replace("_", "")
            if any(
                marker in error_key
                for marker in (
                    "noactivegroupcall",
                    "groupcallnotfound",
                    "group call is not active",
                    "no active group call",
                )
            ):
                detail = (
                    "Telegram did not expose an active voice chat to the assistant. "
                    "Confirm the assistant can access the group and that its voice chat is live."
                )
            else:
                detail = (
                    f"Playback could not start ({error_name}). Check the assistant's "
                    "group permissions, connection, and media source."
                )
            raise AssistantErr(detail)

        # Keep the client that actually succeeded. Previously the first
        # candidate was cached before trying fallbacks, so later controls and
        # queued tracks could target a different assistant and appear stuck.
        self.active_clients[chat_id] = [assistant_to_join]
        await add_active_chat(chat_id)
        await music_on(chat_id)
        if video: await add_active_video_chat(chat_id)

        if await is_autoend(chat_id):
            counter[chat_id] = {}
            try:
                users = len(await assistant_to_join.get_participants(chat_id))
                if users == 1:
                    autoend[chat_id] = datetime.now() + timedelta(minutes=1)
            except: pass

    async def change_stream(self, client, chat_id):
        """Advance the queue safely.

        Older builds recursed into themselves on every download/stream failure
        and left the chat marked as "active" when a play() call raised. That is
        what made the bot look frozen after a few songs (queue kept filling but
        nothing played) until the whole process was restarted on the VPS.
        Now every advance runs under a per-chat lock, failures skip to the next
        track iteratively, and a chat that cannot play anything is fully
        cleaned up instead of being left half-dead.
        """
        lock = self._stream_locks.setdefault(chat_id, asyncio.Lock())
        if lock.locked():
            # Another StreamEnd for the same chat is already being handled.
            return
        async with lock:
            skips = 0
            while True:
                try:
                    result = await self._change_stream_once(client, chat_id)
                except Exception as exception:
                    LOGGER(__name__).error(f"change_stream crashed: {exception}")
                    result = "retry"
                if result != "retry":
                    return result
                skips += 1
                if skips >= 15:
                    LOGGER(__name__).warning(
                        f"Too many failed tracks in {chat_id}; clearing queue."
                    )
                    await self._hard_reset_chat(client, chat_id)
                    return
                await asyncio.sleep(1)

    async def _hard_reset_chat(self, client, chat_id):
        await _clear_(chat_id)
        self.active_clients.pop(chat_id, None)
        self._stream_locks.pop(chat_id, None)
        try:
            await client.leave_call(chat_id)
        except Exception:
            pass

    async def _change_stream_once(self, client, chat_id):
        active_assistants = await self.get_active_clients(chat_id)
        client = active_assistants[0] if active_assistants else client

        check = db.get(chat_id)
        popped = None
        loop = await get_loop(chat_id)

        try:
            if loop == 0:
                if check: popped = check.pop(0)
            else:
                loop = loop - 1
                await set_loop(chat_id, loop)

            if popped: await auto_clean(popped)

            if not db.get(chat_id): 
                if popped and await is_autoplay_on(chat_id):
                    started = await self.autoplay_start(
                        chat_id,
                        popped.get("chat_id", chat_id),
                        popped.get("title"),
                        popped.get("vidid"),
                        client=client,
                        bot_client=popped.get("client", app)
                    )
                    if started:
                        return

                # ✨ FULLY BOLD AND QUOTE FORMATTED LEAVE MESSAGE
                try:
                    bot_to_send = popped.get("client", app) if popped else app
                    original_chat_id = popped.get("chat_id", chat_id) if popped else chat_id
                    
                    leave_msg = (
                        "> **<tg-emoji emoji-id=\"6102493171441209843\">😲</tg-emoji> ᴏᴏᴘs! ᴛʜᴇ ᴍᴜsɪᴄ ǫᴜᴇᴜᴇ ɪs ᴇᴍᴘᴛʏ...**\n"
                        "> ****\n"
                        "> **<tg-emoji emoji-id=\"5217933090483098080\">🎶</tg-emoji> ᴀᴜᴛᴏᴘʟᴀʏ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴏғғ, ᴀɴᴅ ɪ ʜᴀᴠᴇ ɴᴏ ᴍᴏʀᴇ sᴏɴɢs ᴛᴏ ᴘʟᴀʏ.**\n"
                        "> **<tg-emoji emoji-id=\"5298590020796429445\">👋</tg-emoji> ɪ'ᴍ ʟᴇᴀᴠɪɴɢ ᴛʜᴇ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ɴᴏᴡ. ᴛʜᴀɴᴋs ғᴏʀ ʟɪsᴛᴇɴɪɴɢ! <tg-emoji emoji-id=\"6127558265573218459\">❤️</tg-emoji>**"
                    )
                    await bot_to_send.send_message(original_chat_id, leave_msg)
                except Exception as e:
                    LOGGER(__name__).error(f"Failed to send leave message: {e}")

                await _clear_(chat_id)
                if chat_id in self.active_clients: del self.active_clients[chat_id]
                try: await client.leave_call(chat_id) 
                except: pass
                return

        except Exception as e:
            LOGGER(__name__).error(f"❌ Error inside change_stream execution framework: {e}")
            await _clear_(chat_id)
            if chat_id in self.active_clients: del self.active_clients[chat_id]
            try: await client.leave_call(chat_id) 
            except: pass
            return

        if db.get(chat_id):
            queued = db[chat_id][0]["file"]
            original_chat_id = db[chat_id][0]["chat_id"]
            streamtype = db[chat_id][0]["streamtype"]
            videoid = db[chat_id][0]["vidid"]
            chat_client = db[chat_id][0].get("client") or app

            db[chat_id][0]["played"] = 0
            exis = db[chat_id][0].get("old_dur")
            if exis:
                db[chat_id][0]["dur"] = exis
                db[chat_id][0]["seconds"] = db[chat_id][0]["old_second"]
                db[chat_id][0]["speed_path"] = None
                db[chat_id][0]["speed"] = 1.0
            video = True if str(streamtype) == "video" else False

            try:
                language = await get_lang(chat_id)
                _ = get_string(language)
            except:
                _ = get_string("en")

            if not db.get(chat_id): return

            raw_title = db[chat_id][0].get("title")
            title = str(raw_title).title() if raw_title else "Unknown Title"
            raw_user = db[chat_id][0].get("by")
            user = str(raw_user) if raw_user and str(raw_user).strip() else "Unknown User"
            duration_str = db[chat_id][0].get("dur", "0:00")
            user_id = db[chat_id][0].get("user_id", 0) 
            
            try:
                is_clone = (chat_client.me.id != app.me.id) if chat_client.me else False
                bot_username = chat_client.me.username if chat_client.me else app.username
            except:
                is_clone = False
                bot_username = app.username

            if "live_" in queued:
                n, link = await YouTube.video(videoid, True)
                if n == 0:
                    try:
                        await chat_client.send_message(original_chat_id, text=_["call_6"])
                    except Exception:
                        pass
                    return "retry"

                try: await self._safe_change_stream(client, chat_id, link, video)
                except Exception as exception:
                    LOGGER(__name__).warning(f"Stream start failed in {chat_id}: {exception}")
                    try:
                        await chat_client.send_message(original_chat_id, text=_["call_6"])
                    except Exception:
                        pass
                    return "retry"

                button = telegram_markup(_, chat_id)
                try:
                    run = await chat_client.send_photo(
                        chat_id=original_chat_id, photo=get_random_img(config.STREAM_IMG_URL),
                        caption=_["stream_1"].format(f"https://t.me/{bot_username}?start=info_{videoid}", title[:23], duration_str, user),
                        reply_markup=InlineKeyboardMarkup(button)
                    )
                    await attach_player_rich_message(
                        chat_client,
                        run,
                        title=title,
                        duration=duration_str,
                        requested_by=user,
                    )
                    if db.get(chat_id):
                        db[chat_id][0]["mystic"] = run
                        db[chat_id][0]["markup"] = "tg"
                except: pass

            elif "vid_" in queued:
                mystic = await chat_client.send_message(original_chat_id, _["call_7"])

                try:
                    file_path, direct = await YouTube.download(videoid, mystic, videoid=True, video=video)
                except:
                    try: file_path, direct = await YouTube.download(videoid, mystic, videoid=True, video=video)
                    except:
                        try: await mystic.edit_text("⚠️ **YouTube Timeout! Skipping...**", disable_web_page_preview=True)
                        except: pass
                        await asyncio.sleep(2)
                        return "retry"

                if not file_path or str(file_path) == "None":
                    try: await mystic.edit_text("❌ **Error:** Download failed. Skipping track...")
                    except: pass
                    await asyncio.sleep(2)
                    return "retry"

                try: await self._safe_change_stream(client, chat_id, file_path, video)
                except Exception as exception:
                    LOGGER(__name__).warning(f"Stream start failed in {chat_id}: {exception}")
                    try:
                        await chat_client.send_message(original_chat_id, text=_["call_6"])
                    except Exception:
                        pass
                    return "retry"

                img = await get_thumb(videoid, user_id, chat_client) or get_random_img(config.PLAYLIST_IMG_URL)
                
                if is_clone:
                    button = panel_markup_clone(
                        _, videoid, chat_id, bot_username=bot_username
                    )
                else:
                    button = stream_markup(_, chat_id)

                try: await mystic.delete()
                except: pass

                try:
                    run = await chat_client.send_photo(
                        chat_id=original_chat_id, photo=img,
                        caption=_["stream_1"].format(f"https://t.me/{bot_username}?start=info_{videoid}", title[:23], duration_str, user),
                        reply_markup=InlineKeyboardMarkup(button)
                    )
                    await attach_player_rich_message(
                        chat_client,
                        run,
                        title=title,
                        duration=duration_str,
                        requested_by=user,
                    )
                    if db.get(chat_id):
                        db[chat_id][0]["mystic"] = run
                        db[chat_id][0]["markup"] = "stream"
                except: pass

            elif "index_" in queued:
                try: await self._safe_change_stream(client, chat_id, videoid, video)
                except Exception as exception:
                    LOGGER(__name__).warning(f"Stream start failed in {chat_id}: {exception}")
                    try:
                        await chat_client.send_message(original_chat_id, text=_["call_6"])
                    except Exception:
                        pass
                    return "retry"

                button = telegram_markup(_, chat_id)
                try:
                    run = await chat_client.send_photo(
                        chat_id=original_chat_id, photo=get_random_img(config.STREAM_IMG_URL),
                        caption=_["stream_2"].format(user), reply_markup=InlineKeyboardMarkup(button)
                    )
                    await attach_player_rich_message(
                        chat_client,
                        run,
                        title=title,
                        duration=duration_str,
                        requested_by=user,
                    )
                    if db.get(chat_id):
                        db[chat_id][0]["mystic"] = run
                        db[chat_id][0]["markup"] = "tg"
                except: pass

            else:
                try: await self._safe_change_stream(client, chat_id, queued, video)
                except Exception as exception:
                    LOGGER(__name__).warning(f"Stream start failed in {chat_id}: {exception}")
                    try:
                        await chat_client.send_message(original_chat_id, text=_["call_6"])
                    except Exception:
                        pass
                    return "retry"

                if videoid == "telegram":
                    button = telegram_markup(_, chat_id)
                    tg_img = get_random_img(config.TELEGRAM_AUDIO_URL) if not video else get_random_img(config.TELEGRAM_VIDEO_URL)
                    try:
                        run = await chat_client.send_photo(
                            chat_id=original_chat_id, photo=tg_img,
                            caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], duration_str, user),
                            reply_markup=InlineKeyboardMarkup(button)
                        )
                        await attach_player_rich_message(
                            chat_client,
                            run,
                            title=title,
                            duration=duration_str,
                            requested_by=user,
                        )
                        if db.get(chat_id):
                            db[chat_id][0]["mystic"] = run
                            db[chat_id][0]["markup"] = "tg"
                    except: pass

                elif videoid in ["soundcloud", "spotify", "apple", "jiosaavn"]:
                    button = telegram_markup(_, chat_id)
                    try:
                        run = await chat_client.send_photo(
                            chat_id=original_chat_id, photo=get_random_img(config.SOUNCLOUD_IMG_URL),
                            caption=_["stream_1"].format(config.SUPPORT_CHAT, title[:23], duration_str, user),
                            reply_markup=InlineKeyboardMarkup(button)
                        )
                        await attach_player_rich_message(
                            chat_client,
                            run,
                            title=title,
                            duration=duration_str,
                            requested_by=user,
                        )
                        if db.get(chat_id):
                            db[chat_id][0]["mystic"] = run
                            db[chat_id][0]["markup"] = "tg"
                    except: pass

                else:
                    img = await get_thumb(videoid, user_id, chat_client) or get_random_img(config.PLAYLIST_IMG_URL)
                    
                    if is_clone:
                        button = panel_markup_clone(
                            _, videoid, chat_id, bot_username=bot_username
                        )
                    else:
                        button = stream_markup(_, chat_id)
                        
                    try:
                        run = await chat_client.send_photo(
                            chat_id=original_chat_id, photo=img,
                            caption=_["stream_1"].format(f"https://t.me/{bot_username}?start=info_{videoid}", title[:23], duration_str, user),
                            reply_markup=InlineKeyboardMarkup(button)
                        )
                        await attach_player_rich_message(
                            chat_client,
                            run,
                            title=title,
                            duration=duration_str,
                            requested_by=user,
                        )
                        if db.get(chat_id):
                            db[chat_id][0]["mystic"] = run
                            db[chat_id][0]["markup"] = "stream"
                    except: pass

    async def ping(self):
        pings = []
        if getattr(config, "STRING1", None): pings.append(self.one.ping)
        if getattr(config, "STRING2", None): pings.append(self.two.ping)
        if getattr(config, "STRING3", None): pings.append(self.three.ping)
        if getattr(config, "STRING4", None): pings.append(self.four.ping)
        if getattr(config, "STRING5", None): pings.append(self.five.ping)
        return pings

    async def start(self):
        LOGGER(__name__).info("Starting PyTgCalls Client...\n")
        for client in [self.one, self.two, self.three, self.four, self.five]:
            if not client:
                continue
            try:
                await client.start()
                self._started_calls.append(client)
            except Exception:
                LOGGER(__name__).exception("Failed to start one PyTgCalls assistant")
        if not self._started_calls:
            raise RuntimeError("No PyTgCalls assistant could be started")

    async def stop(self):
        for client in reversed(self._started_calls):
            try:
                await client.stop()
            except Exception:
                LOGGER(__name__).warning(
                    "Failed to stop one PyTgCalls assistant", exc_info=True
                )
        self._started_calls.clear()

ANJALI = Call()
