"""Room management for multiplayer games."""

from typing import Dict, Optional, List, Tuple
from uuid import uuid4
import time
import structlog

from models.game_state import GameState, GamePhase
from models.player import Player

logger = structlog.get_logger()

# How long a dropped player's seat is held before the game starts and
# between hands (seconds).
WAITING_GRACE_SECONDS = 120

BOT_DELAYS = {"fast": 0.3, "normal": 1.0, "slow": 2.0}

# Phases in which seats may be changed (before the game and between hands).
SEATING_PHASES = (GamePhase.WAITING, GamePhase.GAME_END)


class Room:
    """
    Represents a game table with four fixed seats (positions 0-3).

    A room manages:
    - Player connections
    - Seats, the table owner and bots
    - Ready status
    - Game state
    """

    def __init__(self, room_id: Optional[str] = None):
        self.room_id = room_id or str(uuid4())
        self.game_state = GameState()
        self.player_sessions: Dict[str, str] = {}  # player_id -> session_id (socket ID)
        self.chat_messages: List[dict] = []  # Chat history (max 100 messages)
        self.owner_id: Optional[str] = None
        self.bot_speed: str = "normal"
        self.turn_seq: int = 0  # Incremented by every game action (guards bot tasks)
        self.last_game_over: Optional[dict] = None  # Result of the hand just played
        self.decision_log: List[dict] = []  # What the bots did this hand and why (for problem reports)
        self.dropped_at: Dict[str, float] = {}  # player_id -> time the connection dropped

    # ------------------------------------------------------------------ seats

    @property
    def players(self) -> List[Player]:
        return self.game_state.players

    def seated(self) -> List[Player]:
        """Players actually at the table (vacated seats excluded)."""
        return [p for p in self.players if not p.vacant]

    def humans(self) -> List[Player]:
        """Seated players that are people (a held seat counts)."""
        return [p for p in self.seated() if not p.is_bot]

    def player_at(self, position: int) -> Optional[Player]:
        return next((p for p in self.players if p.position == position), None)

    def free_seats(self) -> List[int]:
        """Seat numbers nobody sits in (empty or vacated)."""
        taken = {p.position for p in self.seated()}
        return [i for i in range(4) if i not in taken]

    def _sort_players(self) -> None:
        self.players.sort(key=lambda p: p.position)

    def can_change_seats(self) -> bool:
        return self.game_state.phase in SEATING_PHASES

    def _seat_new_player(self, name: str, position: int, is_bot: bool = False) -> Player:
        """Put a new player on a free seat, reusing a vacated seat's totals."""
        old = self.player_at(position)
        if old is not None and not old.vacant:
            raise ValueError("Seat is taken")
        player = Player(name=name, position=position)
        if old is not None:
            # The running total stays with the seat
            player.total_score = old.total_score
            self.players.remove(old)
        if is_bot:
            player.is_bot = True
            player.bot_controlled = True
            player.is_ready = True
        self.players.append(player)
        self._sort_players()
        return player

    def add_player(self, player_name: str, session_id: str) -> Player:
        """
        Add a player to the room on the lowest free seat.

        Raises:
            ValueError: If room is full
        """
        if self.is_full():
            raise ValueError("Room is full (4 players maximum)")
        if not self.can_change_seats():
            raise ValueError("Game in progress")

        player = self._seat_new_player(player_name, self.free_seats()[0])
        self.player_sessions[player.id] = session_id
        if self.owner_id is None:
            self.owner_id = player.id
        return player

    def swap_seats(self, from_position: int, to_position: int) -> None:
        """Move the player on one seat to another seat, swapping if it is taken."""
        if not self.can_change_seats():
            raise ValueError("Seats can only be changed before the game or between hands")
        if from_position == to_position or not all(0 <= p <= 3 for p in (from_position, to_position)):
            raise ValueError("Invalid seat")
        a = self.player_at(from_position)
        b = self.player_at(to_position)
        if a is None or a.vacant:
            raise ValueError("No player on that seat")
        a.position = to_position
        if b is not None:
            b.position = from_position
        self._sort_players()

    def vacate(self, player_id: str) -> None:
        """
        Free a player's seat (before the game or between hands).

        Before the first hand the player is removed. Between hands the seat
        keeps its running total and waits for someone new.
        """
        player = self.game_state.get_player_by_id(player_id)
        if not player:
            return
        self.player_sessions.pop(player_id, None)
        if self.game_state.phase == GamePhase.WAITING:
            self.players.remove(player)
        else:
            player.vacant = True
            player.is_connected = False
            player.is_ready = False
            player.ready_next = False
            player.is_bot = False
            player.bot_controlled = False
        if self.owner_id == player_id:
            self.pass_ownership()

    def pass_ownership(self) -> None:
        """Hand the table to the next connected human in seat order."""
        current = self.game_state.get_player_by_id(self.owner_id) if self.owner_id else None
        start = current.position if current else -1
        for step in range(1, 5):
            candidate = self.player_at((start + step) % 4)
            if (candidate and not candidate.vacant and not candidate.is_bot
                    and candidate.is_connected and candidate.id != self.owner_id):
                self.owner_id = candidate.id
                return
        if current is None or current.vacant or current not in self.players:
            self.owner_id = None

    def is_owner(self, player_id: str) -> bool:
        return self.owner_id is not None and self.owner_id == player_id

    # ------------------------------------------------------------------- bots

    def add_bot(self, position: Optional[int] = None) -> Player:
        """Seat a bot on the given free seat (or the lowest free one)."""
        from bots.names import pick_bot_name

        if not self.can_change_seats():
            raise ValueError("Bots can only be added before the game or between hands")
        free = self.free_seats()
        if not free:
            raise ValueError("Room is full")
        if position is None:
            position = free[0]
        if position not in free:
            raise ValueError("Seat is taken")
        name = pick_bot_name({p.name for p in self.seated()})
        return self._seat_new_player(name, position, is_bot=True)

    def remove_bot(self, position: int) -> None:
        if not self.can_change_seats():
            raise ValueError("Bots can only be removed before the game or between hands")
        player = self.player_at(position)
        if player is None or player.vacant or not player.is_bot:
            raise ValueError("No bot on that seat")
        self.vacate(player.id)

    def fill_bots(self) -> List[Player]:
        return [self.add_bot(pos) for pos in list(self.free_seats())]

    def replace_with_bot(self, position: int) -> Player:
        """Let a bot play a disconnected player's seat. The player may return."""
        player = self.player_at(position)
        if player is None or player.vacant or player.is_bot:
            raise ValueError("No player on that seat")
        if player.is_connected:
            raise ValueError("Player is still connected")
        player.bot_controlled = True
        self.turn_seq += 1
        return player

    # ------------------------------------------------------------ connections

    def reconnect(self, player: Player, new_session_id: str) -> None:
        """Attach a (new) socket to an existing player; the player takes the seat back from a bot."""
        self.player_sessions[player.id] = new_session_id
        player.is_connected = True
        if player.bot_controlled and not player.is_bot:
            player.bot_controlled = False
            self.turn_seq += 1  # cancels a pending bot move for this seat
        if self.owner_id is None:
            self.owner_id = player.id

    def reconnect_player(self, player_name: str, new_session_id: str) -> Optional[Player]:
        """Reconnect an existing player by name."""
        player = self.get_player_by_name(player_name)
        if player:
            self.reconnect(player, new_session_id)
        return player

    def reconnect_player_by_id(self, player_id: str, new_session_id: str) -> Optional[Player]:
        """Reconnect an existing player by ID."""
        player = self.game_state.get_player_by_id(player_id)
        if player and not player.vacant and not player.is_bot:
            self.reconnect(player, new_session_id)
            return player
        return None

    def get_player_by_name(self, player_name: str) -> Optional[Player]:
        """Get a seated human player by name."""
        return next((p for p in self.humans() if p.name == player_name), None)

    def remove_player(self, player_id: str) -> None:
        """Mark a player as disconnected (the seat is kept)."""
        player = self.game_state.get_player_by_id(player_id)
        if player:
            player.is_connected = False
            self.player_sessions.pop(player_id, None)

    def get_player_by_session(self, session_id: str) -> Optional[Player]:
        """Get player by their session ID."""
        player_id = next((pid for pid, sid in self.player_sessions.items() if sid == session_id), None)
        if player_id:
            return self.game_state.get_player_by_id(player_id)
        return None

    # ------------------------------------------------------------------ ready

    def set_player_ready(self, player_id: str, ready: bool = True) -> None:
        player = self.game_state.get_player_by_id(player_id)
        if player:
            player.is_ready = ready

    def is_full(self) -> bool:
        """Check if all four seats are taken."""
        return len(self.seated()) >= 4

    def all_players_ready(self) -> bool:
        return self.is_full() and all(p.is_ready for p in self.seated())

    def can_start_game(self) -> bool:
        """Check if game can start."""
        return self.is_full() and self.all_players_ready() and self.game_state.phase == GamePhase.WAITING

    def can_start_next_hand(self) -> bool:
        """Between hands: every connected human has asked for the next hand."""
        if self.game_state.phase != GamePhase.GAME_END or not self.is_full():
            return False
        waiting_for = [p for p in self.humans() if not p.bot_controlled]
        return (any(p.is_connected for p in waiting_for)
                and all(p.ready_next for p in waiting_for if p.is_connected)
                and all(p.is_connected or p.bot_controlled for p in self.humans()))

    def bot_delay(self) -> float:
        return BOT_DELAYS.get(self.bot_speed, BOT_DELAYS["normal"])

    def get_session_ids(self) -> List[str]:
        return list(self.player_sessions.values())

    # ------------------------------------------------------------------- chat

    def add_chat_message(self, message: dict) -> None:
        self.chat_messages.append(message)
        # Keep only last 100 messages to prevent unbounded growth
        if len(self.chat_messages) > 100:
            self.chat_messages = self.chat_messages[-100:]

    def get_chat_history(self) -> List[dict]:
        return self.chat_messages

    # ------------------------------------------------------------------- info

    def get_room_info(self) -> dict:
        """Get room information for clients."""
        return {
            "room_id": self.room_id,
            "owner_id": self.owner_id,
            "bot_speed": self.bot_speed,
            "phase": self.game_state.phase.value,
            "hand_number": self.game_state.hand_number,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "position": p.position,
                    "is_ready": p.is_ready,
                    "ready_next": p.ready_next,
                    "is_connected": p.is_connected,
                    "is_bot": p.is_bot,
                    "bot_controlled": p.bot_controlled,
                    "total_score": p.total_score,
                }
                for p in self.seated()
            ],
            "is_full": self.is_full(),
            "game_started": self.game_state.phase != GamePhase.WAITING,
        }


class RoomManager:
    """
    Manages all game rooms.

    Singleton pattern for centralized room management.
    """

    def __init__(self):
        self.rooms: Dict[str, Room] = {}
        self.session_to_room: Dict[str, str] = {}  # session_id -> room_id

    def create_room(self, session_id: str, player_name: str) -> Room:
        """Create a new room; the creator takes seat 0 and owns the table."""
        room = Room()
        room.add_player(player_name, session_id)
        self.rooms[room.room_id] = room
        self.session_to_room[session_id] = room.room_id
        return room

    def join_room(self, room_id: str, session_id: str, player_name: str,
                  player_id: str = None) -> Tuple[Room, Player, bool]:
        """
        Join an existing room, or reconnect to a seat already held there.

        Returns:
            (room, player, was_away): was_away is True when the player had
            dropped out (or a bot was playing the seat) and is now back

        Raises:
            ValueError: If room not found or is full
        """
        room = self.rooms.get(room_id)
        if not room:
            raise ValueError(f"Room {room_id} not found")

        # Reconnection: by ID first (more reliable), then by name
        existing = None
        if player_id:
            existing = room.game_state.get_player_by_id(player_id)
            if existing is not None and (existing.vacant or existing.is_bot):
                existing = None
        if existing is None:
            existing = room.get_player_by_name(player_name)

        if existing is not None:
            old_session = room.player_sessions.get(existing.id)
            if old_session and old_session != session_id:
                # A second socket for the same player replaces the first
                self.session_to_room.pop(old_session, None)
            was_away = (not existing.is_connected) or existing.bot_controlled
            room.reconnect(existing, session_id)
            room.dropped_at.pop(existing.id, None)
            self.session_to_room[session_id] = room_id
            return room, existing, was_away

        # New player joining
        if room.is_full():
            raise ValueError("Room is full")

        player = room.add_player(player_name, session_id)
        self.session_to_room[session_id] = room_id
        return room, player, False

    def get_room(self, room_id: str) -> Optional[Room]:
        return self.rooms.get(room_id)

    def get_room_by_session(self, session_id: str) -> Optional[Room]:
        room_id = self.session_to_room.get(session_id)
        if room_id:
            return self.rooms.get(room_id)
        return None

    def _delete_if_no_humans(self, room: Room) -> bool:
        """A table with no human seat left is closed."""
        if not room.humans():
            self.rooms.pop(room.room_id, None)
            for sid in [s for s, rid in self.session_to_room.items() if rid == room.room_id]:
                del self.session_to_room[sid]
            return True
        return False

    def disconnect_session(self, session_id: str) -> Tuple[Optional[Room], Optional[Player]]:
        """
        A socket dropped. The player keeps the seat and is marked disconnected.

        Returns:
            (room, player) or (None, None) if the socket held no seat
        """
        room = self.get_room_by_session(session_id)
        self.session_to_room.pop(session_id, None)
        if not room:
            return None, None
        player = room.get_player_by_session(session_id)
        if not player:
            return room, None
        room.remove_player(player.id)
        room.dropped_at[player.id] = time.time()
        # Mid-game the table must not get stuck without an owner
        if room.is_owner(player.id) and not room.can_change_seats():
            room.pass_ownership()
        return room, player

    def expire_seat(self, room_id: str, player_id: str, now: Optional[float] = None) -> Optional[Room]:
        """
        The grace period for a dropped player ran out. Frees the seat if the
        player is still away and seats may be changed.

        Returns:
            The room if it still exists, else None
        """
        room = self.rooms.get(room_id)
        if not room:
            return None
        player = room.game_state.get_player_by_id(player_id)
        if (player is None or player.vacant or player.is_connected or player.bot_controlled
                or not room.can_change_seats()):
            return room
        if now is not None and now - room.dropped_at.get(player_id, 0) < WAITING_GRACE_SECONDS - 1:
            return room  # came back and dropped again: a newer timer is running
        room.dropped_at.pop(player_id, None)
        room.vacate(player_id)
        if self._delete_if_no_humans(room):
            return None
        return room

    def leave_room(self, session_id: str) -> Optional[Room]:
        """
        A player leaves on purpose.

        Before the game and between hands the seat is freed at once.
        Mid-game the seat is kept (the owner may hand it to a bot).

        Returns:
            The room they left, or None if the room was deleted
        """
        room = self.get_room_by_session(session_id)
        self.session_to_room.pop(session_id, None)
        if not room:
            return None

        player = room.get_player_by_session(session_id)
        if player:
            if room.can_change_seats():
                room.vacate(player.id)
            else:
                room.remove_player(player.id)
                if room.is_owner(player.id):
                    room.pass_ownership()

        if room.can_change_seats() and self._delete_if_no_humans(room):
            return None
        return room

    def get_available_rooms(self) -> List[dict]:
        """Rooms with a free seat, before the game or between hands."""
        return [
            room.get_room_info()
            for room in self.rooms.values()
            if not room.is_full() and room.can_change_seats()
        ]

    def cleanup_disconnected_rooms(self) -> None:
        """Remove rooms where all humans are disconnected and game hasn't started."""
        rooms_to_remove = [
            room_id
            for room_id, room in self.rooms.items()
            if all(not p.is_connected for p in room.humans())
            and room.game_state.phase == GamePhase.WAITING
        ]

        for room_id in rooms_to_remove:
            del self.rooms[room_id]
