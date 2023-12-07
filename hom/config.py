import typing as t
from os import environ

from dotenv import load_dotenv

__all__ = ("Config", "Constants")

load_dotenv()


def _int(var: str) -> int:
    return int(environ[var])


@t.final
class Config:
    __slots__ = ()

    DISCORD_TOKEN: t.Final[str] = environ["DISCORD_TOKEN"]
    SUPPORT_CHANNEL: t.Final[int] = _int("SUPPORT_CHANNEL")
    TICKET_CATEGORY: t.Final[int] = _int("TICKET_CATEGORY")
    MOD_LOG_CHANNEL: t.Final[int] = _int("MOD_LOG_CHANNEL")
    QUESTIONS_CHANNEL: t.Final[int] = _int("QUESTIONS_CHANNEL")
    MOD_ROLE: t.Final[int] = _int("MOD_ROLE")

    def __init__(self) -> None:
        raise RuntimeError("Config should not be instantiated.")


@t.final
class Constants:
    __slots__ = ()

    ARROW: t.Final[str] = "→"
    PREFIX: t.Final[str] = "!"
    DENIED: t.Final[str] = "❌"
    COMPLETE: t.Final[str] = "✅"
    FOOTER: t.Final[str] = (
        "As a reminder, all moderators and admins in this "
        "server volunteer to assist in their free time. "
        "We appreciate your patience.\u200b\n\u200b"
    )

    def __init__(self) -> None:
        raise RuntimeError("Constants should not be instantiated.")
