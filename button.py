from enum import Enum

from ftmgram.enums import ButtonStyle as FTMButtonStyle
from ftmgram.types import InlineKeyboardButton


class ButtonStyle(Enum):
    SUCCESS = FTMButtonStyle.SUCCESS
    PRIMARY = FTMButtonStyle.PRIMARY
    DANGER = FTMButtonStyle.DANGER
    SECONDARY = FTMButtonStyle.DEFAULT
    INFO = FTMButtonStyle.PRIMARY

def styled_button(
    text: str, 
    callback_data: str = None, 
    url: str = None, 
    user_id: int = None, 
    style: ButtonStyle = ButtonStyle.PRIMARY,
    **kwargs
):
    """
    Styled Button: Yeh function style aur extra arguments 
    (jaise icon_custom_emoji_id) ko support karta hai.
    """
    
    # Base arguments setup
    params = {"text": text}
    
    # Callback, URL ya User ID handle karein
    if url:
        params["url"] = url
    elif user_id:
        params["user_id"] = user_id
    elif callback_data:
        params["callback_data"] = callback_data
    else:
        params["callback_data"] = "none"
        
    # Style aur extra arguments add karein (Emoji, etc.)
    params["style"] = style.value if isinstance(style, ButtonStyle) else style
    params.update(kwargs)
    
    return InlineKeyboardButton(**params)
