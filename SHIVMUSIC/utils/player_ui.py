"""Shared rich HTML player card for the main bot and cloned bots.

The photo message keeps the normal inline keyboard for clients that do not
render FTMGram rich buttons.  This companion message uses the HTML button
format requested by the project and is sent directly below the thumbnail.
"""

from html import escape
import logging
from typing import Any

from ftmgram.types import InputRichMessage


LOGGER = logging.getLogger(__name__)


def build_player_rich_message(
    title: Any,
    duration: Any,
    requested_by: Any,
    chat_id: int,
    *,
    playing: bool = True,
) -> InputRichMessage:
    """Build a compact tablet-style HTML player with callback buttons."""
    state_text = "▶️ Playing" if playing else "⏸ Paused"
    toggle_text = "⏸ Pause" if playing else "▶️ Play"
    safe_title = escape(str(title or "Unknown track"))
    safe_duration = escape(str(duration or "Unknown"))
    safe_requester = escape(str(requested_by or "Unknown"))

    html = f"""
<b>🎧 LIVE PLAYER</b><br/>
<blockquote><b>{safe_title}</b><br/>⏱ {safe_duration} · 👤 {safe_requester}<br/><b>{state_text}</b></blockquote>
<tg-button-row align="center">
  <tg-button type="callback_data" style="primary" data="ADMIN Replay|{chat_id}">⏮ Previous</tg-button>
  <tg-button type="callback_data" style="success" data="ADMIN Toggle|{chat_id}">{toggle_text}</tg-button>
  <tg-button type="callback_data" style="primary" data="ADMIN Skip|{chat_id}">⏭ Next</tg-button>
</tg-button-row>
<tg-button-row align="center">
  <tg-button type="callback_data" style="secondary" data="ADMIN Autoplay|{chat_id}">🔁 Auto-play</tg-button>
  <tg-button type="callback_data" style="secondary" data="close">✕ Close</tg-button>
</tg-button-row>
"""
    return InputRichMessage(html=html.strip())


async def send_player_rich_message(
    client: Any,
    chat_id: int,
    *,
    title: Any,
    duration: Any,
    requested_by: Any,
    playing: bool = True,
    reply_to_message_id: int | None = None,
) -> Any:
    """Send the HTML player without breaking the normal photo player."""
    try:
        message = await client.send_rich_message(
            chat_id=chat_id,
            rich_message=build_player_rich_message(
                title,
                duration,
                requested_by,
                chat_id,
                playing=playing,
            ),
            reply_to_message_id=reply_to_message_id,
        )
        return message
    except Exception as exception:
        # Rich buttons are an enhancement; the standard inline keyboard remains
        # usable on older clients or older FTMGram deployments.
        LOGGER.warning("HTML player message was not sent: %s", exception)
        return None


async def attach_player_rich_message(
    client: Any,
    player_message: Any,
    *,
    title: Any,
    duration: Any,
    requested_by: Any,
    playing: bool = True,
) -> Any:
    """Place the rich HTML controls directly beneath a sent thumbnail."""
    if not player_message:
        return None
    return await send_player_rich_message(
        client,
        player_message.chat.id,
        title=title,
        duration=duration,
        requested_by=requested_by,
        playing=playing,
        reply_to_message_id=player_message.id,
    )