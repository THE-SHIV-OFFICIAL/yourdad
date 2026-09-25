import random
from typing import Union
from ftmgram import filters, types, Client
from ftmgram.types import InlineKeyboardMarkup, Message
from ftmgram.errors import MessageNotModified

from SHIVMUSIC import app
from SHIVMUSIC.utils.inline.help import help_back_markup, private_help_panel, clone_help_panel, clone_back_markup
from SHIVMUSIC.utils import first_page
from SHIVMUSIC.utils import help_pannel
from SHIVMUSIC.utils.database import get_lang
from SHIVMUSIC.utils.decorators.language import LanguageStart, languageCB
from config import BANNED_USERS, HELP_IMG_URL, SUPPORT_CHAT
from strings import get_string, helpers
from SHIVMUSIC.utils.stuffs.helper import Helper
from SHIVMUSIC.utils.database.clonedb import get_owner_id_from_db, get_cloned_support_chat, get_cloned_support_channel
from SHIVMUSIC.utils.rich_helper import legacy_help_to_rich

# ✅ Helper to safe get Random Image
def get_random_help_img():
    if HELP_IMG_URL:
        if isinstance(HELP_IMG_URL, list):
            return random.choice(HELP_IMG_URL)
        return HELP_IMG_URL
    return "https://files.catbox.moe/10zwqs.jpg" # Fallback

@Client.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
@Client.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(
    client: app, update: Union[types.Message, types.CallbackQuery]
):
    bot = await client.get_me()
    
    C_BOT_OWNER_ID = await get_owner_id_from_db(bot.id)
    
    C_BOT_SUPPORT_CHAT = await get_cloned_support_chat(bot.id)
    C_SUPPORT_CHAT = f"https://t.me/{C_BOT_SUPPORT_CHAT}"
    
    is_callback = isinstance(update, types.CallbackQuery)
    
    user_id = update.from_user.id
    is_owner = (user_id == C_BOT_OWNER_ID)

    if is_callback:
        try:
            await update.answer()
        except:
            pass
        chat_id = update.message.chat.id
        language = await get_lang(chat_id)
        _ = get_string(language)
        
        keyboard = first_page(_, is_owner)
        
        try:
            await client.edit_message_text(
                chat_id=update.message.chat.id,
                message_id=update.message.id,
                rich_message=legacy_help_to_rich(_["help_1"].format(C_SUPPORT_CHAT)),
                reply_markup=keyboard,
            )
        except MessageNotModified:
            pass
    else:
        try:
            await update.delete()
        except:
            pass
        language = await get_lang(update.chat.id)
        _ = get_string(language)
        
        keyboard = first_page(_, is_owner)
        
        await client.send_rich_message(
            chat_id=update.chat.id,
            rich_message=legacy_help_to_rich(_["help_1"].format(C_SUPPORT_CHAT)),
            reply_markup=keyboard,
            reply_to_message_id=update.id,
        )


@Client.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    # ✅ FIX: Removed the redundant InlineKeyboardMarkup wrapper here
    await message.reply_text(_["help_2"], reply_markup=keyboard)


@Client.on_callback_query(filters.regex("help_callback") & ~BANNED_USERS)
@languageCB
async def helper_cb(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    
    keyboard = help_back_markup(_)
    clone_back_kb = clone_back_markup(_)
    
    try:
        help_text = getattr(helpers, f"HELP_{cb.removeprefix('hb')}", None)
        if help_text:
            await client.edit_message_text(
                chat_id=CallbackQuery.message.chat.id,
                message_id=CallbackQuery.message.id,
                rich_message=legacy_help_to_rich(help_text),
                reply_markup=keyboard,
            )
        
        # --- CLONE OWNER MENU ---
        elif cb == "chelp":
            clone_kb = clone_help_panel(_)
            await client.edit_message_text(chat_id=CallbackQuery.message.chat.id, message_id=CallbackQuery.message.id, rich_message=legacy_help_to_rich(helpers.CLONE_HELP_MENU), reply_markup=clone_kb)

        elif cb == "clone_manage":
            await client.edit_message_text(chat_id=CallbackQuery.message.chat.id, message_id=CallbackQuery.message.id, rich_message=legacy_help_to_rich(helpers.CLONE_MANAGE), reply_markup=clone_back_kb)

        elif cb == "clone_start":
            await client.edit_message_text(chat_id=CallbackQuery.message.chat.id, message_id=CallbackQuery.message.id, rich_message=legacy_help_to_rich(helpers.CLONE_START), reply_markup=clone_back_kb)
        
        elif cb == "clone_ping":
            await client.edit_message_text(chat_id=CallbackQuery.message.chat.id, message_id=CallbackQuery.message.id, rich_message=legacy_help_to_rich(helpers.CLONE_PING), reply_markup=clone_back_kb)

        elif cb == "clone_buttons":
            # Merged Button & Rename Help
            await client.edit_message_text(chat_id=CallbackQuery.message.chat.id, message_id=CallbackQuery.message.id, rich_message=legacy_help_to_rich(helpers.CLONE_BUTTONS), reply_markup=clone_back_kb)

        # ✅ Added New Play Mode Help
        elif cb == "clone_play":
            await client.edit_message_text(chat_id=CallbackQuery.message.chat.id, message_id=CallbackQuery.message.id, rich_message=legacy_help_to_rich(helpers.CLONE_PLAY_MODE), reply_markup=clone_back_kb)

        elif cb == "clone_logger":
            await client.edit_message_text(chat_id=CallbackQuery.message.chat.id, message_id=CallbackQuery.message.id, rich_message=legacy_help_to_rich(helpers.CLONE_LOGGER), reply_markup=clone_back_kb)
            
    except MessageNotModified:
        pass
    except Exception as e:
        print(f"Help Menu Error: {e}")
