"""Room management for multiplayer games."""

from typing import Dict, Optional, List
from uuid import uuid4
from models.game_state import GameState, GamePhase
from models.player import Player


class Room:
    """
    Represents a game room for 4 players.

    A room manages:
    - Player connections
    - Ready status
    - Game state
    """

    def __init__(self, room_id: Optional[str] = None):
        self.room_id = room_id or str(uuid4())
        self.game_state = GameState()
        self.player_sessions: Dict[str, str] = {}  # player_id -> session_id (socket ID)

    def add_player(self, player_name: str, session_id: str) -> Player:
        """
        Add a player to the room.

        Args:
            player_name: Name of the player
            session_id: WebSocket session ID

        Returns:
            The created Player object

        Raises:
            ValueError: If room is full
        """
        if self.is_full():
            raise ValueError("Room is full (4 players maximum)")

        player = Player(name=player_name, position=len(self.game_state.players))
        self.game_state.add_player(player)
        self.player_sessions[player.id] = session_id

        return player

    def reconnect_player(self, player_name: str, new_session_id: str) -> Optional[Player]:
        """
        Reconnect an existing player with a new session ID.

        Args:
            player_name: Name of the player reconnecting
            new_session_id: New WebSocket session ID

        Returns:
            The reconnected Player object, or None if player not found
        """
        # Find player by name
        player = next((p for p in self.game_state.players if p.name == player_name), None)

        if player:
            # Update session ID
            self.player_sessions[player.id] = new_session_id
            # Mark as connected
            player.is_connected = True
            return player

        return None

    def reconnect_player_by_id(self, player_id: str, new_session_id: str) -> Optional[Player]:
        """
        Reconnect an existing player by ID with a new session ID.

        Args:
            player_id: ID of the player reconnecting
            new_session_id: New WebSocket session ID

        Returns:
            The reconnected Player object, or None if player not found
        """
        # Find player by ID
        player = self.game_state.get_player_by_id(player_id)

        if player:
            # Update session ID
            old_session = self.player_sessions.get(player.id)
            self.player_sessions[player.id] = new_session_id
            # Mark as connected
            player.is_connected = True
            print(f"[Room] Reconnected player {player.name} (ID: {player_id})")
            print(f"[Room]   Old session: {old_session}")
            print(f"[Room]   New session: {new_session_id}")
            print(f"[Room]   Position: {player.position}")
            return player

        print(f"[Room] Failed to reconnect player by ID: {player_id} (not found)")
        return None

    def get_player_by_name(self, player_name: str) -> Optional[Player]:
        """
        Get player by their name.

        Args:
            player_name: Name of the player

        Returns:
            Player or None
        """
        return next((p for p in self.game_state.players if p.name == player_name), None)

    def remove_player(self, player_id: str) -> None:
        """
        Remove a player from the room.

        Args:
            player_id: ID of player to remove
        """
        player = self.game_state.get_player_by_id(player_id)
        if player:
            player.is_connected = False
            if player_id in self.player_sessions:
                del self.player_sessions[player_id]

    def get_player_by_session(self, session_id: str) -> Optional[Player]:
        """
        Get player by their session ID.

        Args:
            session_id: WebSocket session ID

        Returns:
            Player or None
        """
        player_id = next((pid for pid, sid in self.player_sessions.items() if sid == session_id), None)
        if player_id:
            return self.game_state.get_player_by_id(player_id)
        return None

    def set_player_ready(self, player_id: str, ready: bool = True) -> None:
        """
        Set a player's ready status.

        Args:
            player_id: ID of player
            ready: Ready status
        """
        player = self.game_state.get_player_by_id(player_id)
        if player:
            player.is_ready = ready

    def is_full(self) -> bool:
        """Check if room has 4 players."""
        return len(self.game_state.players) >= 4

    def all_players_ready(self) -> bool:
        """Check if all players are ready to start."""
        return self.game_state.all_players_ready()

    def can_start_game(self) -> bool:
        """Check if game can start."""
        return self.is_full() and self.all_players_ready() and self.game_state.phase == GamePhase.WAITING

    def get_session_ids(self) -> List[str]:
        """Get all session IDs in this room."""
        return list(self.player_sessions.values())

    def get_room_info(self) -> dict:
        """
        Get room information for clients.

        Returns:
            Dictionary with room info
        """
        return {
            "room_id": self.room_id,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "position": p.position,
                    "is_ready": p.is_ready,
                    "is_connected": p.is_connected,
                }
                for p in self.game_state.players
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
        """
        Create a new room and add the creator as first player.

        Args:
            session_id: Creator's session ID
            player_name: Creator's name

        Returns:
            The created Room
        """
        room = Room()
        player = room.add_player(player_name, session_id)
        self.rooms[room.room_id] = room
        self.session_to_room[session_id] = room.room_id

        return room

    def join_room(self, room_id: str, session_id: str, player_name: str, player_id: str = None) -> Room:
        """
        Join an existing room.

        Args:
            room_id: ID of room to join
            session_id: Player's session ID
            player_name: Player's name
            player_id: Optional player ID for reconnection (more reliable than name)

        Returns:
            The joined Room

        Raises:
            ValueError: If room not found or is full
        """
        room = self.rooms.get(room_id)
        if not room:
            raise ValueError(f"Room {room_id} not found")

        # Check for reconnection - try by ID first (more reliable), then by name
        existing_player = None
        if player_id:
            print(f"[RoomManager] Checking for reconnection by ID: {player_id}")
            existing_player = room.game_state.get_player_by_id(player_id)
            if existing_player:
                print(f"[RoomManager] Found existing player by ID, reconnecting...")
                # This is a reconnection by ID - update session ID
                player = room.reconnect_player_by_id(player_id, session_id)
                self.session_to_room[session_id] = room_id
                return room
            else:
                print(f"[RoomManager] No player found with ID: {player_id}")

        # Try to find by name
        print(f"[RoomManager] Checking for reconnection by name: {player_name}")
        existing_player = room.get_player_by_name(player_name)
        if existing_player:
            print(f"[RoomManager] Found existing player by name, reconnecting...")
            # This is a reconnection by name - update session ID
            player = room.reconnect_player(player_name, session_id)
            self.session_to_room[session_id] = room_id
            return room

        # New player joining
        if room.is_full():
            raise ValueError("Room is full")

        player = room.add_player(player_name, session_id)
        self.session_to_room[session_id] = room_id

        return room

    def get_room(self, room_id: str) -> Optional[Room]:
        """Get room by ID."""
        return self.rooms.get(room_id)

    def get_room_by_session(self, session_id: str) -> Optional[Room]:
        """Get room for a session."""
        room_id = self.session_to_room.get(session_id)
        if room_id:
            return self.rooms.get(room_id)
        return None

    def leave_room(self, session_id: str) -> Optional[Room]:
        """
        Remove a player from their room.

        Args:
            session_id: Session ID of player leaving

        Returns:
            The room they left, or None if room was deleted
        """
        room = self.get_room_by_session(session_id)
        if not room:
            return None

        player = room.get_player_by_session(session_id)
        game_not_started = room.game_state.phase == GamePhase.WAITING

        if player:
            if game_not_started:
                # Game hasn't started - actually remove player from room
                room.game_state.players = [p for p in room.game_state.players if p.id != player.id]
                if player.id in room.player_sessions:
                    del room.player_sessions[player.id]

                # Update positions of remaining players
                for i, p in enumerate(room.game_state.players):
                    p.position = i
            else:
                # Game in progress - just mark as disconnected (allow reconnection)
                room.remove_player(player.id)

        # Clean up session mapping
        if session_id in self.session_to_room:
            del self.session_to_room[session_id]

        # Remove empty rooms
        if len(room.game_state.players) == 0:
            del self.rooms[room.room_id]
            return None

        return room

    def get_available_rooms(self) -> List[dict]:
        """
        Get list of available rooms (not full, not started).

        Returns:
            List of room info dictionaries
        """
        return [
            room.get_room_info()
            for room in self.rooms.values()
            if not room.is_full() and room.game_state.phase == GamePhase.WAITING
        ]

    def cleanup_disconnected_rooms(self) -> None:
        """Remove rooms where all players are disconnected and game hasn't started."""
        rooms_to_remove = [
            room_id
            for room_id, room in self.rooms.items()
            if all(not p.is_connected for p in room.game_state.players)
            and room.game_state.phase == GamePhase.WAITING
        ]

        for room_id in rooms_to_remove:
            del self.rooms[room_id]
