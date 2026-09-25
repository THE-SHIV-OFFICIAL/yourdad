"""Reusable Telegram Rich Message layouts used by main and clone bots."""

import asyncio
from html import escape
import re

from ftmgram.enums import ParseMode
from ftmgram.types import InputRichMessage


EMOJI = {
    "sparkle": "<tg-emoji emoji-id='6172312314423808834'>✨</tg-emoji>",
    "book": "<tg-emoji emoji-id='5260512129240276089'>📚</tg-emoji>",
    "chart": "<tg-emoji emoji-id='5936143551854285132'>📊</tg-emoji>",
    "command": "<tg-emoji emoji-id='6172663483834831848'>⌨️</tg-emoji>",
    "info": "<tg-emoji emoji-id='5188540541922480562'>❓</tg-emoji>",
    "music": "<tg-emoji emoji-id='6082387600599944892'>🎧</tg-emoji>",
}


def _cell(value: object, *, header: bool = False) -> str:
    tag = "th" if header else "td"
    return f"<{tag}>{escape(str(value))}</{tag}>"


def rich_table(title: str, headers: list[str], rows: list[tuple[object, ...]], note: str | None = None) -> InputRichMessage:
    head = "".join(_cell(item, header=True) for item in headers)
    body = "".join(
        f"<tr>{''.join(_cell(item) for item in row)}</tr>" for row in rows
    )
    note_html = (
        f"<br/><i>{EMOJI['music']} {escape(str(note))}</i>" if note else ""
    )
    html = (
        f"<b>{EMOJI['sparkle']} {escape(title)} {EMOJI['sparkle']}</b>\n"
        f"<table><tr>{head}</tr>{body}</table>\n{note_html}"
    )
    return InputRichMessage(html=html)


def build_rich_stats(title: str, stats_dict: dict[str, object]) -> InputRichMessage:
    return rich_table(
        title,
        ["Metric", "Value"],
        [(key, value) for key, value in stats_dict.items()],
        f"{EMOJI['music']} Live system information",
    )


def build_rich_help(title: str, rows: list[tuple[str, str]], note: str | None = None) -> InputRichMessage:
    return rich_table(title, ["Command", "Description"], rows, note)


def legacy_help_to_rich(text: str) -> InputRichMessage:
    """Turn an existing help block into the same bordered two-column layout."""
    clean = re.sub(r"<[^>]+>", "", text).strip()
    lines = [line.strip(" •") for line in clean.splitlines() if line.strip()]
    title = lines.pop(0).strip(" :") if lines else "Commands"
    rows: list[tuple[str, str]] = []
    notes: list[str] = []
    for line in lines:
        if " – " in line:
            command, description = line.split(" – ", 1)
            rows.append((command.strip(), description.strip()))
        elif line.startswith("/") and " " in line:
            command, description = line.split(" ", 1)
            rows.append((command.strip(), description.strip(" :-")))
        else:
            notes.append(line)
    if not rows:
        rows = [("Info", line) for line in notes] or [("Info", "No commands available")]
        notes = []
    return build_rich_help(title, rows, "\n".join(notes) or None)


def markdown_to_html(text: str) -> str:
    """Convert the legacy Markdown markers used by translations into HTML."""
    value = str(text or "")
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value, flags=re.DOTALL)
    value = re.sub(r"__(.+?)__", r"<u>\1</u>", value, flags=re.DOTALL)
    value = re.sub(r"~~(.+?)~~", r"<s>\1</s>", value, flags=re.DOTALL)
    value = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", value)
    return value


_HTML_OR_TEXT_TOKEN = re.compile(
    r"</?[^>]+>|&(?:#[0-9]+|#x[0-9a-fA-F]+|[A-Za-z][A-Za-z0-9]+);|.",
    re.DOTALL,
)
_VOID_TAGS = {"br", "hr", "img", "meta", "link", "input"}


def _typewriter_frames(full_html: str, steps: int = 4) -> list[str]:
    """Create valid, balanced HTML prefixes so animation never exposes broken tags."""
    source = str(full_html or "")
    tokens = _HTML_OR_TEXT_TOKEN.findall(source)
    visible_tokens = [
        token for token in tokens if not (token.startswith("<") and token.endswith(">"))
    ]
    if not visible_tokens:
        return [source]

    frames: list[str] = []
    for step in range(1, max(2, steps)):
        reveal_to = max(1, (len(visible_tokens) * step) // steps)
        output: list[str] = []
        open_tags: list[str] = []
        revealed = 0
        for token in tokens:
            if token.startswith("<") and token.endswith(">"):
                match = re.match(r"<\s*(/?)\s*([a-zA-Z][\w:-]*)\b[^>]*>", token)
                if match:
                    closing, tag_name = match.groups()
                    tag_name = tag_name.lower()
                    if closing:
                        output.append(token)
                        if tag_name in open_tags:
                            open_tags.reverse()
                            open_tags.remove(tag_name)
                            open_tags.reverse()
                    else:
                        output.append(token)
                        if not token.rstrip().endswith("/>") and tag_name not in _VOID_TAGS:
                            open_tags.append(tag_name)
                else:
                    output.append(token)
                continue

            if revealed >= reveal_to:
                break
            output.append(token)
            revealed += 1

        output.extend(f"</{tag}>" for tag in reversed(open_tags))
        frame = "".join(output)
        if frame and (not frames or frames[-1] != frame):
            frames.append(frame)

    if not frames or frames[-1] != source:
        frames.append(source)
    return frames


async def stream_typewriter_rich_message(
    client,
    chat_id: int,
    full_html: str,
    *,
    reply_to_message_id: int | None = None,
    chunk_delay: float = 0.08,
    steps: int = 4,
):
    """Send a short HTML typewriter animation, then leave the completed message."""
    frames = _typewriter_frames(full_html, steps=steps)
    if not frames:
        return None

    try:
        message = await client.send_rich_message(
            chat_id=chat_id,
            rich_message=InputRichMessage(html=frames[0]),
            reply_to_message_id=reply_to_message_id,
        )
    except Exception:
        # Keep the start command usable on older FTMGram builds without RichMessage.
        message = await client.send_message(
            chat_id=chat_id,
            text=frames[0],
            parse_mode=ParseMode.HTML,
            reply_to_message_id=reply_to_message_id,
        )

    for frame in frames[1:]:
        if chunk_delay:
            await asyncio.sleep(chunk_delay)
        try:
            await client.edit_message_text(
                chat_id=chat_id,
                message_id=message.id,
                rich_message=InputRichMessage(html=frame),
            )
        except Exception:
            try:
                await message.edit_text(frame, parse_mode=ParseMode.HTML)
            except Exception:
                # An edit limitation should not stop /start from continuing.
                break
    return message

