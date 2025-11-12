"""SQLite persistence layer for game rooms and states."""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
import structlog
from datetime import datetime

logger = structlog.get_logger()


class GameDatabase:
    """SQLite database for persisting game state."""

    def __init__(self, db_path: str = "data/tarokk_game.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        # Create data directory if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self._init_schema()
        logger.info("database_initialized", path=db_path)

    def _init_schema(self):
        """Create database schema if it doesn't exist."""
        cursor = self.conn.cursor()

        # Rooms table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                room_id TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Players table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                position INTEGER NOT NULL,
                is_connected INTEGER DEFAULT 0,
                is_ready INTEGER DEFAULT 0,
                session_id TEXT,
                FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
            )
        """)

        # Game states table (stores JSON blob of entire game state)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_states (
                room_id TEXT PRIMARY KEY,
                phase TEXT NOT NULL,
                current_turn INTEGER NOT NULL,
                dealer_position INTEGER NOT NULL,
                declarer_position INTEGER,
                partner_position INTEGER,
                partner_revealed INTEGER DEFAULT 0,
                called_card_rank TEXT,
                trick_number INTEGER DEFAULT 0,
                game_data JSON NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
            )
        """)

        # Chat messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                room_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (room_id) REFERENCES rooms(room_id) ON DELETE CASCADE
            )
        """)

        # Create indices for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_players_room
            ON players(room_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_room
            ON chat_messages(room_id, timestamp)
        """)

        self.conn.commit()
        logger.info("database_schema_created")

    def save_room(self, room_id: str) -> None:
        """
        Save or update a room.

        Args:
            room_id: Room ID to save
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO rooms (room_id, last_activity)
            VALUES (?, CURRENT_TIMESTAMP)
            ON CONFLICT(room_id) DO UPDATE SET
                last_activity = CURRENT_TIMESTAMP
        """, (room_id,))
        self.conn.commit()

    def save_player(self, player: Dict[str, Any], room_id: str, session_id: Optional[str] = None) -> None:
        """
        Save or update a player.

        Args:
            player: Player data dictionary
            room_id: Room ID the player belongs to
            session_id: Optional session ID for the player
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO players (player_id, room_id, name, position, is_connected, is_ready, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_id) DO UPDATE SET
                name = excluded.name,
                position = excluded.position,
                is_connected = excluded.is_connected,
                is_ready = excluded.is_ready,
                session_id = excluded.session_id
        """, (
            player['id'],
            room_id,
            player['name'],
            player['position'],
            player.get('is_connected', False),
            player.get('is_ready', False),
            session_id
        ))
        self.conn.commit()

    def save_game_state(self, room_id: str, game_state_dict: Dict[str, Any]) -> None:
        """
        Save complete game state.

        Args:
            room_id: Room ID
            game_state_dict: Game state as dictionary (from to_dict())
        """
        cursor = self.conn.cursor()

        # Extract key fields for indexing
        phase = game_state_dict.get('phase', 'waiting')
        current_turn = game_state_dict.get('current_turn', 0)
        dealer_position = game_state_dict.get('dealer_position', 0)
        declarer_position = game_state_dict.get('declarer_position')
        partner_position = game_state_dict.get('partner_position')
        partner_revealed = game_state_dict.get('partner_revealed', False)
        called_card_rank = game_state_dict.get('called_card_rank')
        trick_number = game_state_dict.get('trick_number', 0)

        cursor.execute("""
            INSERT INTO game_states (
                room_id, phase, current_turn, dealer_position,
                declarer_position, partner_position, partner_revealed,
                called_card_rank, trick_number, game_data, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(room_id) DO UPDATE SET
                phase = excluded.phase,
                current_turn = excluded.current_turn,
                dealer_position = excluded.dealer_position,
                declarer_position = excluded.declarer_position,
                partner_position = excluded.partner_position,
                partner_revealed = excluded.partner_revealed,
                called_card_rank = excluded.called_card_rank,
                trick_number = excluded.trick_number,
                game_data = excluded.game_data,
                updated_at = CURRENT_TIMESTAMP
        """, (
            room_id,
            phase,
            current_turn,
            dealer_position,
            declarer_position,
            partner_position,
            partner_revealed,
            called_card_rank,
            trick_number,
            json.dumps(game_state_dict)
        ))
        self.conn.commit()

    def save_chat_message(self, room_id: str, chat_message: Dict[str, Any]) -> None:
        """
        Save a chat message.

        Args:
            room_id: Room ID
            chat_message: Chat message dictionary
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO chat_messages (id, room_id, player_name, message, timestamp)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
        """, (
            chat_message['id'],
            room_id,
            chat_message['player_name'],
            chat_message['message'],
            chat_message['timestamp']
        ))
        self.conn.commit()

    def load_all_rooms(self) -> List[Dict[str, Any]]:
        """
        Load all active rooms from database.

        Returns:
            List of room data dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT r.room_id, r.created_at, r.last_activity
            FROM rooms r
            WHERE r.is_active = 1
            ORDER BY r.last_activity DESC
        """)

        rooms = []
        for row in cursor.fetchall():
            room_data = {
                'room_id': row['room_id'],
                'created_at': row['created_at'],
                'last_activity': row['last_activity'],
                'players': self.load_players(row['room_id']),
                'game_state': self.load_game_state(row['room_id']),
                'chat_messages': self.load_chat_messages(row['room_id'])
            }
            rooms.append(room_data)

        logger.info("loaded_rooms_from_database", count=len(rooms))
        return rooms

    def load_players(self, room_id: str) -> List[Dict[str, Any]]:
        """
        Load all players for a room.

        Args:
            room_id: Room ID

        Returns:
            List of player dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT player_id, name, position, is_connected, is_ready, session_id
            FROM players
            WHERE room_id = ?
            ORDER BY position
        """, (room_id,))

        players = []
        for row in cursor.fetchall():
            players.append({
                'id': row['player_id'],
                'name': row['name'],
                'position': row['position'],
                'is_connected': bool(row['is_connected']),
                'is_ready': bool(row['is_ready']),
                'session_id': row['session_id']
            })

        return players

    def load_game_state(self, room_id: str) -> Optional[Dict[str, Any]]:
        """
        Load game state for a room.

        Args:
            room_id: Room ID

        Returns:
            Game state dictionary or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT game_data
            FROM game_states
            WHERE room_id = ?
        """, (room_id,))

        row = cursor.fetchone()
        if row:
            return json.loads(row['game_data'])
        return None

    def load_chat_messages(self, room_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Load chat messages for a room.

        Args:
            room_id: Room ID
            limit: Maximum number of messages to load

        Returns:
            List of chat message dictionaries
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id, player_name, message, timestamp
            FROM chat_messages
            WHERE room_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (room_id, limit))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'id': row['id'],
                'player_name': row['player_name'],
                'message': row['message'],
                'timestamp': row['timestamp']
            })

        return messages

    def delete_room(self, room_id: str) -> None:
        """
        Mark a room as inactive (soft delete).

        Args:
            room_id: Room ID to delete
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE rooms
            SET is_active = 0
            WHERE room_id = ?
        """, (room_id,))
        self.conn.commit()
        logger.info("room_marked_inactive", room_id=room_id)

    def hard_delete_room(self, room_id: str) -> None:
        """
        Permanently delete a room and all associated data.

        Args:
            room_id: Room ID to delete
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM rooms WHERE room_id = ?", (room_id,))
        self.conn.commit()
        logger.info("room_deleted", room_id=room_id)

    def cleanup_old_rooms(self, days: int = 7) -> int:
        """
        Delete rooms that haven't been active for specified days.

        Args:
            days: Number of days of inactivity before deletion

        Returns:
            Number of rooms deleted
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM rooms
            WHERE is_active = 0
            AND last_activity < datetime('now', '-' || ? || ' days')
        """, (days,))

        deleted_count = cursor.rowcount
        self.conn.commit()

        if deleted_count > 0:
            logger.info("cleaned_up_old_rooms", count=deleted_count, days=days)

        return deleted_count

    def mark_all_players_disconnected(self) -> None:
        """Mark all players as disconnected (call on server startup)."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE players
            SET is_connected = 0, session_id = NULL
        """)
        self.conn.commit()
        logger.info("marked_all_players_disconnected")

    def update_player_session(self, player_id: str, session_id: str, is_connected: bool = True) -> None:
        """
        Update player session ID and connection status.

        Args:
            player_id: Player ID
            session_id: New session ID
            is_connected: Connection status
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE players
            SET session_id = ?, is_connected = ?
            WHERE player_id = ?
        """, (session_id, is_connected, player_id))
        self.conn.commit()

    def get_room_by_player_id(self, player_id: str) -> Optional[str]:
        """
        Get room ID for a player.

        Args:
            player_id: Player ID

        Returns:
            Room ID or None
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT room_id
            FROM players
            WHERE player_id = ?
        """, (player_id,))

        row = cursor.fetchone()
        return row['room_id'] if row else None

    def close(self):
        """Close database connection."""
        self.conn.close()
        logger.info("database_connection_closed")
