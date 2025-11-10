"""Announcement model for Hungarian Tarokk bonuses."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class AnnouncementType(str, Enum):
    """Types of announcements/bonuses in Hungarian Tarokk."""
    TRULL = "trull"                      # All 3 honours (skíz, XXI, pagát)
    FOUR_KINGS = "four_kings"            # All 4 Kings
    DOUBLE_GAME = "double_game"          # Predicting 71+ points
    VOLAT = "volat"                      # Predicting winning all 9 tricks
    PAGAT_ULTIMO = "pagat_ultimo"        # Pagát wins last trick
    XXI_CATCH = "xxi_catch"              # Skíz captures opponent's XXI


class Announcement(BaseModel):
    """
    Represents an announcement made by a player.

    Attributes:
        player_position: Position (0-3) of the player making the announcement
        announcement_type: Type of announcement
        announced: Whether it was announced (True) or silent (False)
        points: Points value for this announcement
    """
    player_position: int
    announcement_type: AnnouncementType
    announced: bool = True  # True = announced, False = silent

    def get_points(self) -> int:
        """
        Get the point value for this announcement.

        Points are higher if announced vs silent.
        """
        points_map = {
            AnnouncementType.TRULL: 2 if self.announced else 1,
            AnnouncementType.FOUR_KINGS: 2 if self.announced else 1,
            AnnouncementType.DOUBLE_GAME: 0,  # Multiplies game value instead
            AnnouncementType.VOLAT: 0,  # Multiplies game value instead
            AnnouncementType.PAGAT_ULTIMO: 10 if self.announced else 5,
            AnnouncementType.XXI_CATCH: 42 if self.announced else 21,
        }
        return points_map.get(self.announcement_type, 0)

    def get_multiplier(self) -> int:
        """
        Get the game value multiplier for this announcement.

        Some announcements multiply the base game value.
        Returns 1 if no multiplier effect.
        """
        if self.announcement_type == AnnouncementType.DOUBLE_GAME:
            return 2 if self.announced else 1  # Doubles if announced
        elif self.announcement_type == AnnouncementType.VOLAT:
            return 3 if self.announced else 1  # Triples if announced
        return 1

    def to_dict(self) -> dict:
        """Convert announcement to dictionary for JSON serialization."""
        return {
            "player_position": self.player_position,
            "announcement_type": self.announcement_type.value,
            "announced": self.announced,
            "points": self.get_points(),
            "multiplier": self.get_multiplier(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Announcement":
        """Create announcement from dictionary."""
        return cls(
            player_position=data["player_position"],
            announcement_type=AnnouncementType(data["announcement_type"]),
            announced=data.get("announced", True)
        )

    def __str__(self) -> str:
        """String representation of announcement."""
        announced_str = "announced" if self.announced else "silent"
        return f"{self.announcement_type.value} ({announced_str})"

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Announcement(player={self.player_position}, type={self.announcement_type.value}, announced={self.announced})"
