"""Dependency-light regression tests for the rich UI and clone error fallback."""

import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _install_ftmgram_stubs():
    package = types.ModuleType("ftmgram")
    package.__path__ = []
    package.Client = type("Client", (), {})

    enums = types.ModuleType("ftmgram.enums")
    enums.ParseMode = types.SimpleNamespace(HTML="html")

    message_types = types.ModuleType("ftmgram.types")

    class InputRichMessage:
        def __init__(self, *, html):
            self.html = html

    message_types.InputRichMessage = InputRichMessage
    sys.modules["ftmgram"] = package
    sys.modules["ftmgram.enums"] = enums
    sys.modules["ftmgram.types"] = message_types
    return InputRichMessage


InputRichMessage = _install_ftmgram_stubs()


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rich = _load_module(
    "rich_helper_under_test",
    ROOT / "SHIVMUSIC" / "utils" / "rich_helper.py",
)
exceptions = _load_module(
    "exceptions_under_test",
    ROOT / "SHIVMUSIC" / "utils" / "exceptions.py",
)


class RichUiTests(unittest.TestCase):
    def test_ping_stats_show_plain_bot_name_not_html_anchor(self):
        message = rich.build_rich_stats("Pong: 12.5 ms", {"Bot": "@music_clone"})
        self.assertIn("@music_clone", message.html)
        self.assertNotIn("<a href=", message.html)
        self.assertNotIn("&lt;a href=", message.html)
        self.assertNotIn("<blockquote", message.html)

    def test_legacy_markdown_is_converted_before_html_rendering(self):
        rendered = rich.markdown_to_html(
            "**Premium music** `play` <tg-emoji emoji-id='123'>🎧</tg-emoji>"
        )
        self.assertIn("<b>Premium music</b>", rendered)
        self.assertIn("<code>play</code>", rendered)
        self.assertIn("<tg-emoji", rendered)

    def test_typewriter_frames_are_balanced_and_finish_at_full_html(self):
        source = (
            "<blockquote><b><tg-emoji emoji-id='1'>✨</tg-emoji> Welcome</b>"
            "<br/><i>Loading clone settings</i></blockquote>"
        )
        frames = rich._typewriter_frames(source, steps=4)
        self.assertGreaterEqual(len(frames), 2)
        self.assertEqual(frames[-1], source)

        for frame in frames:
            open_tags = []
            for token in rich._HTML_OR_TEXT_TOKEN.findall(frame):
                if not (token.startswith("<") and token.endswith(">")):
                    continue
                match = rich.re.match(
                    r"<\s*(/?)\s*([a-zA-Z][\w:-]*)\b[^>]*>", token
                )
                if not match:
                    continue
                closing, tag = match.groups()
                tag = tag.lower()
                if closing:
                    self.assertTrue(open_tags, f"unexpected closing tag in {frame}")
                    self.assertEqual(open_tags.pop(), tag, f"unbalanced frame: {frame}")
                elif not token.rstrip().endswith("/>") and tag not in rich._VOID_TAGS:
                    open_tags.append(tag)
            self.assertEqual(open_tags, [], f"unclosed tags in frame: {frame}")

    def test_typewriter_updates_message_until_final_html(self):
        class FakeMessage:
            id = 42

            async def edit_text(self, text, **kwargs):
                self.last_text = text

        class FakeClient:
            def __init__(self):
                self.sent = None
                self.edits = []
                self.message = FakeMessage()

            async def send_rich_message(self, **kwargs):
                self.sent = kwargs["rich_message"].html
                return self.message

            async def edit_message_text(self, **kwargs):
                self.edits.append(kwargs["rich_message"].html)

        client = FakeClient()
        source = "<b>✨ Rich welcome screen</b>"
        result = asyncio.run(
            rich.stream_typewriter_rich_message(
                client, 10, source, chunk_delay=0, steps=3
            )
        )
        self.assertIs(result, client.message)
        self.assertTrue(client.edits)
        self.assertEqual(client.edits[-1], source)


class VoiceChatClassificationTests(unittest.TestCase):
    def test_permissions_are_not_misreported_as_voice_chat_off(self):
        class ChatAdminRequired(Exception):
            pass

        class CreateGroupCall(Exception):
            pass

        self.assertFalse(
            exceptions.is_voice_chat_unavailable(ChatAdminRequired("admin required"))
        )
        self.assertFalse(
            exceptions.is_voice_chat_unavailable(CreateGroupCall("permission denied"))
        )
        self.assertFalse(
            exceptions.is_voice_chat_unavailable(
                RuntimeError("voice chat is on but assistant cannot access it")
            )
        )

    def test_explicit_missing_call_is_classified(self):
        class NoActiveGroupCall(Exception):
            pass

        self.assertTrue(
            exceptions.is_voice_chat_unavailable(NoActiveGroupCall("not active"))
        )
        self.assertTrue(
            exceptions.is_voice_chat_unavailable(
                RuntimeError("No active group call found")
            )
        )


class CloneErrorFallbackTests(unittest.TestCase):
    def test_clone_report_retries_through_primary_bot(self):
        config_stub = types.ModuleType("config")
        config_stub.ERROR_LOGGER_ID = -100123
        config_stub.LOGGER_ID = 0
        sys.modules["config"] = config_stub
        errors = _load_module(
            "error_logger_under_test",
            ROOT / "SHIVMUSIC" / "error_logger.py",
        )

        class FakeClient:
            def __init__(self, label, fail=False):
                self.error_logger_name = label
                self.fail = fail
                self.messages = []

            async def send_message(self, **kwargs):
                if self.fail:
                    raise RuntimeError("not a member of error group")
                self.messages.append(kwargs)

        clone = FakeClient("Clone @sample_music", fail=True)
        main = FakeClient("Primary music bot")
        errors._main_client = main

        asyncio.run(
            errors.report_exception(
                clone,
                RuntimeError("playback failed"),
                context="clone playback",
            )
        )

        self.assertEqual(len(clone.messages), 0)
        self.assertEqual(len(main.messages), 1)
        report = main.messages[0]["text"]
        self.assertIn("Clone @sample_music", report)
        self.assertIn("playback failed", report)


if __name__ == "__main__":
    unittest.main()