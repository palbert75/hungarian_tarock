"""Message protocol for Hungarian Tarokk server."""

from enum import Enum
from typing import Any, Optional, Dict
from pydantic import BaseModel


class MessageType(str, Enum):
    """Message types for client-server communication."""

    # Connection
    CONNECT = "connect"
    DISCONNECT = "disconnect"

    # Lobby/Room
    CREATE_ROOM = "create_room"
    JOIN_ROOM = "join_room"
    LEAVE_ROOM = "leave_room"
    READY = "ready"
    ROOM_STATE = "room_state"

    # Game Flow
    GAME_STARTED = "game_started"
    GAME_STATE = "game_state"
    YOUR_TURN = "your_turn"

    # Bidding
    PLACE_BID = "place_bid"
    BID_PLACED = "bid_placed"
    BIDDING_COMPLETE = "bidding_complete"

    # Talon & Discard
    TALON_DISTRIBUTED = "talon_distributed"
    DISCARD_CARDS = "discard_cards"
    PLAYER_DISCARDED = "player_discarded"

    # Partner
    CALL_PARTNER = "call_partner"
    PARTNER_CALLED = "partner_called"
    PARTNER_REVEALED = "partner_revealed"

    # Announcements
    MAKE_ANNOUNCEMENT = "make_announcement"
    ANNOUNCEMENT_MADE = "announcement_made"
    PASS_ANNOUNCEMENT = "pass_announcement"
    CONTRA_ANNOUNCEMENT = "contra_announcement"
    CONTRA_MADE = "contra_made"
    RECONTRA_ANNOUNCEMENT = "recontra_announcement"
    RECONTRA_MADE = "recontra_made"
    ANNOUNCEMENTS_COMPLETE = "announcements_complete"

    # Trick-taking
    PLAY_CARD = "play_card"
    CARD_PLAYED = "card_played"
    TRICK_STARTED = "trick_started"
    TRICK_COMPLETE = "trick_complete"

    # Scoring
    GAME_OVER = "game_over"

    # Errors
    ERROR = "error"


class Message(BaseModel):
    """Base message structure."""
    type: MessageType
    data: Optional[Dict[str, Any]] = None

    @classmethod
    def create(cls, msg_type: MessageType, **kwargs) -> "Message":
        """Create a message with data."""
        return cls(type=msg_type, data=kwargs)

    def to_dict(self) -> dict:
        """Convert message to dictionary for JSON serialization."""
        return {
            "type": self.type.value,
            "data": self.data or {}
        }


# Client -> Server Messages

class JoinRoomMessage(BaseModel):
    """Join room message from client."""
    player_name: str
    room_id: Optional[str] = None  # If None, create new room


class PlaceBidMessage(BaseModel):
    """Place bid message from client."""
    bid_type: str  # "three", "two", "one", "solo", "pass", "hold"


class DiscardCardsMessage(BaseModel):
    """Discard cards message from client."""
    card_ids: list[str]


class CallPartnerMessage(BaseModel):
    """Call partner message from client."""
    tarokk_rank: str  # e.g., "XX"


class MakeAnnouncementMessage(BaseModel):
    """Make announcement message from client."""
    announcement_type: str  # e.g., "trull", "four_kings", etc.
    announced: bool = True  # True = announced, False = silent


class PlayCardMessage(BaseModel):
    """Play card message from client."""
    card_id: str


# Server -> Client Messages

class RoomStateMessage(BaseModel):
    """Room state message to client."""
    room_id: str
    players: list[dict]
    is_full: bool
    game_started: bool


class GameStateMessage(BaseModel):
    """Game state message to client."""
    game_id: str
    phase: str
    current_turn: int
    dealer_position: int
    your_position: int
    your_hand: list[dict]
    players: list[dict]
    bid_history: list[dict]
    declarer_position: Optional[int]
    partner_revealed: bool
    trick_number: int
    current_trick: list[dict]


class YourTurnMessage(BaseModel):
    """Your turn notification to client."""
    valid_actions: list[str]
    valid_bids: Optional[list[str]] = None
    valid_cards: Optional[list[str]] = None
    must_play_tarokk: bool = False


class BidPlacedMessage(BaseModel):
    """Bid placed notification."""
    player_position: int
    bid_type: str


class TalonDistributedMessage(BaseModel):
    """Talon distributed notification."""
    you_received: int
    your_hand_size: int


class PlayerDiscardedMessage(BaseModel):
    """Player discarded notification."""
    player_position: int
    num_cards: int
    tarokks_discarded: int


class PartnerCalledMessage(BaseModel):
    """Partner called notification."""
    called_card: str


class AnnouncementMadeMessage(BaseModel):
    """Announcement made notification."""
    player_position: int
    announcement_type: str
    announced: bool


class CardPlayedMessage(BaseModel):
    """Card played notification."""
    player_position: int
    card: dict


class TrickCompleteMessage(BaseModel):
    """Trick complete notification."""
    winner: int
    cards: list[dict]
    points_in_trick: int
    partner_revealed: bool


class GameOverMessage(BaseModel):
    """Game over notification."""
    declarer: int
    partner: int
    declarer_team_points: int
    opponent_team_points: int
    winner: str
    game_value: int
    bonuses: list[dict]
    payments: dict[str, int]


class ErrorMessage(BaseModel):
    """Error message."""
    code: str
    message: str
    details: Optional[dict] = None


def create_error_message(code: str, message: str, **details) -> Message:
    """
    Create an error message.

    Args:
        code: Error code
        message: Error message
        **details: Additional error details

    Returns:
        Error message
    """
    return Message.create(
        MessageType.ERROR,
        code=code,
        message=message,
        details=details or None
    )
