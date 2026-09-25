import logging
from typing import Dict, List, Union, Optional
from SHIVMUSIC.core.mongo import mongodb

LOGGER = logging.getLogger(__name__)

# ==========================================
#            MONGODB COLLECTIONS
# ==========================================
cloneownerdb = mongodb.cloneownerdb
clonebotnamedb = mongodb.clonebotnamedb
chatsdbc = mongodb.chatsc
usersdbc = mongodb.tgusersdbc
clonebotdb = mongodb.clonebotdb
clone_custom_db = mongodb.clone_custom_settings

# ==========================================
#        GLOBAL CLONE MANAGEMENT
# ==========================================

def get_all_clones():
    """Returns cursor for all clone bots."""
    return clonebotdb.find()

async def save_clonebot_owner(bot_id: Union[int, str], user_id: int):
    """Saves the owner ID of a clone bot."""
    try:
        await cloneownerdb.update_one(
            {"bot_id": int(bot_id)},
            {"$set": {"user_id": int(user_id)}},
            upsert=True
        )
    except Exception as e:
        LOGGER.error(f"Error in save_clonebot_owner: {e}")

async def get_clonebot_owner(bot_id: Union[int, str]) -> Optional[int]:
    """Retrieves the owner ID of a clone bot (From Owner DB)."""
    try:
        query = {"bot_id": {"$in": [int(bot_id), str(bot_id)]}}
        result = await cloneownerdb.find_one(query)
        if result:
            return result.get("user_id")
    except Exception as e:
        LOGGER.error(f"Error in get_clonebot_owner: {e}")
    return None

async def save_clonebot_username(bot_id: Union[int, str], user_name: str):
    """Saves the username of a clone bot."""
    try:
        await clonebotnamedb.update_one(
            {"bot_id": int(bot_id)},
            {"$set": {"user_name": str(user_name)}},
            upsert=True
        )
    except Exception as e:
        LOGGER.error(f"Error in save_clonebot_username: {e}")

async def get_clonebot_username(bot_id: Union[int, str]) -> Optional[str]:
    """Retrieves the username of a clone bot."""
    try:
        result = await clonebotnamedb.find_one({"bot_id": int(bot_id)})
        if result:
            return result.get("user_name")
    except Exception as e:
        LOGGER.error(f"Error in get_clonebot_username: {e}")
    return None

async def get_owner_id_from_db(bot_id: Union[int, str]) -> Optional[int]:
    """Retrieves owner ID directly from the main clone DB."""
    try:
        bot_data = await clonebotdb.find_one({"bot_id": int(bot_id)})
        if bot_data:
            return bot_data.get("user_id")
    except Exception as e:
        LOGGER.error(f"Error in get_owner_id_from_db: {e}")
    return None

async def get_cloned_support_chat(bot_id: Union[int, str]) -> str:
    """Retrieves the support chat link for a clone bot."""
    try:
        bot_details = await clonebotdb.find_one({"bot_id": int(bot_id)})
        if bot_details:
            return bot_details.get("support", "No support chat set.")
    except Exception as e:
        LOGGER.error(f"Error in get_cloned_support_chat: {e}")
    return "No support chat set."

async def get_cloned_support_channel(bot_id: Union[int, str]) -> str:
    """Retrieves the support channel link for a clone bot."""
    try:
        bot_details = await clonebotdb.find_one({"bot_id": int(bot_id)})
        if bot_details:
            return bot_details.get("channel", "No channel set.")
    except Exception as e:
        LOGGER.error(f"Error in get_cloned_support_channel: {e}")
    return "No channel set."

async def has_user_cloned_any_bot(user_id: int) -> bool:
    """Checks if a user has created any clone bot."""
    try:
        cloned_bot = await clonebotdb.find_one({"user_id": int(user_id)})
        if cloned_bot:
            return True
    except Exception as e:
        LOGGER.error(f"Error in has_user_cloned_any_bot: {e}")
    return False

# ==========================================
#      CUSTOMIZATION (PLAY/SEARCH)
# ==========================================

async def set_clone_search_type(bot_id: Union[int, str], type_name: str, content: str):
    """
    Saves the search message preference.
    type_name: 'text', 'sticker', 'animation', 'video', 'photo'
    content: The text message or file_id (supports ||| list)
    """
    try:
        await clone_custom_db.update_one(
            {"bot_id": int(bot_id)},
            {"$set": {type_name: content}}, # Updates specific field
            upsert=True
        )
    except Exception as e:
        LOGGER.error(f"Error in set_clone_search_type: {e}")

async def get_clone_search_type(bot_id: Union[int, str], type_name: str) -> Optional[str]:
    """Retrieves raw content for a specific type (used for append logic)."""
    try:
        data = await clone_custom_db.find_one({"bot_id": int(bot_id)})
        if data:
            return data.get(type_name)
    except Exception as e:
        LOGGER.error(f"Error in get_clone_search_type: {e}")
    return None

async def get_clone_search_settings(bot_id: Union[int, str]):
    """
    Retrieves the HIGHEST PRIORITY search preference for Play Mode.
    Priority: Video > Photo > Animation > Sticker > Text
    Returns: (type_name, content)
    """
    try:
        data = await clone_custom_db.find_one({"bot_id": int(bot_id)})
        if not data:
            return None, None
        
        # Priority Logic
        if data.get("video"):
            return "video", data.get("video")
        if data.get("photo"):
            return "photo", data.get("photo")
        if data.get("animation"):
            return "animation", data.get("animation")
        if data.get("sticker"):
            return "sticker", data.get("sticker")
        if data.get("text"):
            return "text", data.get("text")
    except Exception as e:
        LOGGER.error(f"Error in get_clone_search_settings: {e}")
        
    return None, None

async def delete_clone_search_type(bot_id: Union[int, str]):
    """Deletes ALL search mode settings (Reset to default)."""
    try:
        await clone_custom_db.update_one(
            {"bot_id": int(bot_id)},
            {"$unset": {
                "video": "",
                "photo": "",
                "animation": "",
                "sticker": "",
                "text": ""
            }}
        )
    except Exception as e:
        LOGGER.error(f"Error in delete_clone_search_type: {e}")

# --- Stream Caption ---

async def set_clone_stream_caption(bot_id: Union[int, str], caption: str):
    """Saves the custom stream caption."""
    try:
        await clone_custom_db.update_one(
            {"bot_id": int(bot_id)},
            {"$set": {"stream_caption": caption}},
            upsert=True
        )
    except Exception as e:
        LOGGER.error(f"Error in set_clone_stream_caption: {e}")

async def get_clone_stream_caption(bot_id: Union[int, str]) -> Optional[str]:
    """Retrieves the custom stream caption."""
    try:
        data = await clone_custom_db.find_one({"bot_id": int(bot_id)})
        if data:
            return data.get("stream_caption")
    except Exception as e:
        LOGGER.error(f"Error in get_clone_stream_caption: {e}")
    return None

async def delete_clone_stream_caption(bot_id: Union[int, str]):
    """Deletes the custom stream caption."""
    try:
        await clone_custom_db.update_one(
            {"bot_id": int(bot_id)},
            {"$unset": {"stream_caption": ""}}
        )
    except Exception as e:
        LOGGER.error(f"Error in delete_clone_stream_caption: {e}")

# ==========================================
#        BROADCAST HELPERS
# ==========================================

async def get_served_chats_clone(bot_id: Union[int, str]) -> List[Dict]:
    """Fetches all chats served by a specific clone bot."""
    served_chats = []
    try:
        query = {"bot_id": {"$in": [int(bot_id), str(bot_id)]}}
        async for chat in chatsdbc.find(query):
            served_chats.append(chat)
    except Exception as e:
        LOGGER.error(f"Error in get_served_chats_clone: {e}")
    return served_chats

async def get_served_users_clone(bot_id: Union[int, str]) -> List[Dict]:
    """Fetches all users served by a specific clone bot."""
    served_users = []
    try:
        query = {"bot_id": {"$in": [int(bot_id), str(bot_id)]}}
        async for user in usersdbc.find(query):
            served_users.append(user)
    except Exception as e:
        LOGGER.error(f"Error in get_served_users_clone: {e}")
    return served_users
