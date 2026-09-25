class AssistantErr(Exception):
    def __init__(self, errr: str):
        super().__init__(errr)


def is_voice_chat_unavailable(error: BaseException) -> bool:
    """Return true only for explicit missing/inactive group-call errors.

    Permission errors such as CHAT_ADMIN_REQUIRED and CREATE_GROUP_CALL are
    reported separately; they must not be presented as proof that a voice
    chat is switched off.
    """
    name = type(error).__name__.lower().replace("_", "")
    message = str(error).lower().replace("_", "")
    markers = (
        "noactivegroupcall",
        "groupcallnotfound",
        "groupcallinvalid",
        "no active group call",
        "group call not found",
    )
    return any(marker in name or marker in message for marker in markers)
