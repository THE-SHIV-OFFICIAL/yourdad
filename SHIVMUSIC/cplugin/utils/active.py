# ✅ FIX: db import kiya taaki play.py ke sath sync rahe
from SHIVMUSIC.misc import db

active = []
stream = {}


async def is_active_chat(chat_id: int) -> bool:
    # Optimized: If-else ki zaroorat nahi hai, direct boolean return karega
    return chat_id in active


async def add_active_chat(chat_id: int):
    if chat_id not in active:
        active.append(chat_id)


async def remove_active_chat(chat_id: int):
    if chat_id in active:
        active.remove(chat_id)


async def get_active_chats() -> list:
    return active


async def is_streaming(chat_id: int) -> bool:
    # Optimized: Seedha dict se False ya True return karega
    return bool(stream.get(chat_id, False))


async def iss_streaming(chat_id: int) -> bool:
    return bool(stream.get(chat_id, False))


async def stream_on(chat_id: int):
    stream[chat_id] = True


async def stream_off(chat_id: int):
    stream[chat_id] = False


async def _clear_(chat_id):
    try:
        # ✅ FIX 1: db clear kar rahe hain (clonedb nahi)
        db[chat_id] = []
        
        # ✅ FIX 2: Active list se remove karna
        await remove_active_chat(chat_id)
        
        # ✅ FIX 3 (NEW): Stream status ko dictionary se hatana bohot zaroori hai
        # Warna cache memory full hogi aur previous state stuck reh jayegi
        if chat_id in stream:
            stream.pop(chat_id)
            
    except Exception as e:
        print(f"Error in _clear_: {e}")  # Taki error aaye to terminal me dikh jaye, bot silent na rahe
        return
