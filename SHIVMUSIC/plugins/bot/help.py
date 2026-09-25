import random
from typing import Union
from ftmgram import filters, types, enums
from ftmgram.types import InlineKeyboardMarkup, Message, InlineKeyboardButton
from SHIVMUSIC import app
from SHIVMUSIC.utils import help_pannel
from SHIVMUSIC.utils.database import get_lang
from SHIVMUSIC.utils.decorators.language import LanguageStart, languageCB
from SHIVMUSIC.utils.inline.help import help_back_markup, private_help_panel
from SHIVMUSIC.utils.rich_helper import legacy_help_to_rich
from config import BANNED_USERS, START_IMG_URL, SUPPORT_CHAT
from strings import get_string, helpers
from SHIVMUSIC.utils.stuffs.helper import Helper

# ✅ Helper to safe get Random Image
def get_random_start_img():
    if START_IMG_URL:
        if isinstance(START_IMG_URL, list):
            return random.choice(START_IMG_URL)
        return START_IMG_URL
    return "https://telegra.ph/file/2e3d368e77c449c287430.jpg" # Fallback

@app.on_message(filters.command(["help"]) & filters.private & ~BANNED_USERS)
@app.on_callback_query(filters.regex("settings_back_helper") & ~BANNED_USERS)
async def helper_private(
    client: app, update: Union[types.Message, types.CallbackQuery]
):
    is_callback = isinstance(update, types.CallbackQuery)
    if is_callback:
        try:
            await update.answer()
        except:
            pass
        chat_id = update.message.chat.id
        language = await get_lang(chat_id)
        _ = get_string(language)
        keyboard = help_pannel(_, True)
        
        # Callback just edits text, no spoiler needed here
        await client.edit_message_text(
            chat_id=update.message.chat.id,
            message_id=update.message.id,
            rich_message=legacy_help_to_rich(_["help_1"].format(SUPPORT_CHAT)),
            reply_markup=keyboard,
        )
    else:
        try:
            await update.delete()
        except:
            pass
        language = await get_lang(update.chat.id)
        _ = get_string(language)
        keyboard = help_pannel(_)
        
        await client.send_rich_message(
            chat_id=update.chat.id,
            rich_message=legacy_help_to_rich(_["help_1"].format(SUPPORT_CHAT)),
            reply_markup=keyboard,
            reply_to_message_id=update.id,
        )


@app.on_message(filters.command(["help"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def help_com_group(client, message: Message, _):
    keyboard = private_help_panel(_)
    # ✅ FIX: Removed the redundant InlineKeyboardMarkup() wrapper
    await message.reply_text(_["help_2"], reply_markup=keyboard)


@app.on_callback_query(filters.regex("help_callback") & ~BANNED_USERS)
@languageCB
async def helper_cb(client, CallbackQuery, _):
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    keyboard = help_back_markup(_)
    
    help_text = getattr(helpers, f"HELP_{cb.removeprefix('hb')}", None)
    if help_text:
        await client.edit_message_text(
            chat_id=CallbackQuery.message.chat.id,
            message_id=CallbackQuery.message.id,
            rich_message=legacy_help_to_rich(help_text),
            reply_markup=keyboard,
        )


@app.on_callback_query(filters.regex('managebot123'))
async def on_back_button(client, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    
    # We need to get language here to pass to help_pannel
    language = await get_lang(CallbackQuery.message.chat.id)
    _ = get_string(language)
    
    keyboard = help_pannel(_, True)
    if cb == "settings_back_helper":
        await CallbackQuery.edit_message_text(
            _["help_1"].format(SUPPORT_CHAT), reply_markup=keyboard
        )

@app.on_callback_query(filters.regex('mplus'))      
async def mb_plugin_button(client, CallbackQuery):
    callback_data = CallbackQuery.data.strip()
    cb = callback_data.split(None, 1)[1]
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ʙᴀᴄᴋ", callback_data=f"mbot_cb")]])
    if cb == "Okieeeeee":
        await CallbackQuery.edit_message_text(f"`something errors`", reply_markup=keyboard, parse_mode=enums.ParseMode.MARKDOWN)
    else:
        await CallbackQuery.edit_message_text(getattr(Helper, cb), reply_markup=keyboard)
