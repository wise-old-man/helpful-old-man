import typing as t
from os import environ

__all__ = ("Config", "Constants")


@t.final
class Config:
    __slots__ = ()

    WOM_GUILD: t.Final[int] = int(environ["WOM_GUILD"])
    DISCORD_TOKEN: t.Final[str] = environ["DISCORD_TOKEN"]
    STICKY_CHANNEL: t.Final[int] = int(environ["STICKY_CHANNEL"])
    TICKET_CATEGORY: t.Final[int] = int(environ["TICKET_CATEGORY"])

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
        raise RuntimeError("Config should not be instantiated.")
