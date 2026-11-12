"""Names for bot players."""

from typing import Set

BOT_NAMES = ["Bot Jani", "Bot Kati", "Bot Pista", "Bot Juli", "Bot Feri", "Bot Marcsi"]


def pick_bot_name(taken: Set[str]) -> str:
    """First bot name not already used at the table."""
    for name in BOT_NAMES:
        if name not in taken:
            return name
    n = 2
    while f"Bot {n}" in taken:
        n += 1
    return f"Bot {n}"
