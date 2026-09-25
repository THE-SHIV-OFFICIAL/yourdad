# Shiv Music Clone Repair Notes

## Changes

- Voice-chat errors are no longer treated as “VC off” when Telegram reports
  missing assistant permissions such as `CHAT_ADMIN_REQUIRED` or
  `CREATE_GROUP_CALL`. The bot now gives an access/permission diagnosis and
  reserves the inactive-chat response for explicit missing-call errors.
- Playback now records the PyTgCalls assistant that actually started the
  stream. Failed candidates are not retained as the active assistant, avoiding
  follow-up controls and queue changes being sent to a stale client.
- Failed playback attempts are sent to the central error logger. If a clone or
  assistant cannot post to that group, the primary bot retries the report while
  the report still identifies the originating clone/account.
- `/ping` displays a plain `@username` (or bot ID) inside the rich stats table,
  rather than rendering an HTML mention as visible source markup. The ping
  latency now uses a monotonic timer, and the footer no longer uses the
  quote-style block that appeared awkward in the supplied screenshot.
- Main and clone private `/start` loading messages use the same balanced-HTML
  typewriter helper. Legacy `**bold**` text in start captions is converted to
  HTML before HTML-mode rendering.

## Verification

- `python -m compileall -q SHIVMUSIC tests` — passed.
- `python -m unittest discover -s tests -v` — 7 regression tests passed.
- Live Telegram/PyTgCalls playback was not run here: this workspace has no
  installed FTMGram runtime, Telegram sessions, bot credentials, or live group
  call. Verify one audio play and one clone play after deploying, then test
  pause/resume and queue advance in a group where the assistant has access.

## Deployment checks

1. Install the project's pinned/runtime dependencies and restart the bot.
2. Ensure the primary bot can post to `ERROR_LOGGER_ID` (or `LOGGER_ID`).
3. Ensure the assistant is in the music group and can access its voice chat.
4. Test `/play`, `/pause`, `/resume`, `/skip`, and `/ping` with both the main
   bot and a clone.