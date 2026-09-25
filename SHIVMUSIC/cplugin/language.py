"""Language controls for cloned bot clients.

The main bot loads plugins/tools/language.py, but clones only load cplugin.
Keeping these handlers in cplugin makes the same language buttons available
when a clone is running.
"""

from ftmgram import Client, filters
from ftmgram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from SHIVMUSIC.utils.database import get_lang, set_lang
from SHIVMUSIC.utils.decorators.language import language, languageCB
from SHIVMUSIC.cplugin.utils.decorators.admins import ActualAdminCB
from config import BANNED_USERS
from strings import get_string, languages_present


def languages_keyboard(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=languages_present[lang],
                callback_data=f"languages:{lang}",
            )
        ]
        for lang in languages_present
    ]
    buttons.append(
        [
            InlineKeyboardButton(text=_["BACK_BUTTON"], callback_data="settings_helper"),
            InlineKeyboardButton(text=_["CLOSE_BUTTON"], callback_data="close"),
        ]
    )
    return InlineKeyboardMarkup(buttons)


@Client.on_message(filters.command(["lang", "setlang", "language"]) & ~BANNED_USERS)
@language
async def langs_command(client: Client, message: Message, _):
    await message.reply_text(_["lang_1"], reply_markup=languages_keyboard(_))


@Client.on_callback_query(filters.regex(r"^LG$") & ~BANNED_USERS)
@languageCB
async def language_menu(client, callback_query, _):
    await callback_query.answer()
    return await callback_query.edit_message_reply_markup(
        reply_markup=languages_keyboard(_)
    )


@Client.on_callback_query(filters.regex(r"^languages:(.+)$") & ~BANNED_USERS)
@ActualAdminCB
async def language_markup(client, callback_query, _):
    lang = callback_query.data.split(":", 1)[1]
    old_lang = await get_lang(callback_query.message.chat.id)

    if lang == old_lang:
        return await callback_query.answer(_["lang_4"], show_alert=True)

    try:
        strings = get_string(lang)
    except Exception:
        return await callback_query.answer(_["lang_3"], show_alert=True)

    await set_lang(callback_query.message.chat.id, lang)
    await callback_query.answer(_["lang_2"], show_alert=True)
    return await callback_query.edit_message_reply_markup(
        reply_markup=languages_keyboard(strings)
    )