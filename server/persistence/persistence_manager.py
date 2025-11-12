"""Persistence manager for coordinating room and game state persistence."""

import asyncio
from typing import Optional, Dict, Any
import structlog
from datetime import datetime

from persistence.database import GameDatabase
from networking.room_manager import Room, RoomManager
from models.game_state import GameState, GamePhase
from models.player import Player
from models.card import Card
from models.bid import Bid, BidType
from models.announcement import Announcement, AnnouncementType

logger = structlog.get_logger()


class PersistenceManager:
    """
    Manages persistence of game rooms and state.

    Provides:
    - Auto-save after state changes
    - Load rooms on startup
    - Coordinated saves across room, players, game state, and chat
    """

    def __init__(self, db_path: str = "data/tarokk_game.db"):
        """
        Initialize persistence manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db = GameDatabase(db_path)
        self._save_queue: Dict[str, float] = {}  # room_id -> last_save_time
        self._save_lock = asyncio.Lock()
        logger.info("persistence_manager_initialized")

    async def save_room_complete(self, room: Room) -> None:
        """
        Save complete room state including players, game state, and chat.

        Args:
            room: Room object to save
        """
        try:
            async with self._save_lock:
                # Save room metadata
                self.db.save_room(room.room_id)

                # Save all players
                for player in room.game_state.players:
                    player_dict = {
                        'id': player.id,
                        'name': player.name,
                        'position': player.position,
                        'is_connected': player.is_connected,
                        'is_ready': player.is_ready,
                    }
                    session_id = room.player_sessions.get(player.id)
                    self.db.save_player(player_dict, room.room_id, session_id)

                # Save game state
                game_state_dict = room.game_state.to_dict(include_all_hands=True)
                self.db.save_game_state(room.room_id, game_state_dict)

                # Note: Chat messages are saved individually in real-time
                # to avoid data loss, so we don't need to save them here

                logger.debug("room_saved", room_id=room.room_id,
                           phase=room.game_state.phase.value,
                           players=len(room.game_state.players))

        except Exception as e:
            logger.error("save_room_error", room_id=room.room_id, error=str(e))

    def save_chat_message(self, room_id: str, chat_message: Dict[str, Any]) -> None:
        """
        Save a single chat message immediately.

        Args:
            room_id: Room ID
            chat_message: Chat message dictionary
        """
        try:
            self.db.save_chat_message(room_id, chat_message)
        except Exception as e:
            logger.error("save_chat_message_error", room_id=room_id, error=str(e))

    async def load_all_rooms(self, room_manager: RoomManager) -> int:
        """
        Load all persisted rooms into the room manager.

        Args:
            room_manager: RoomManager instance to populate

        Returns:
            Number of rooms loaded
        """
        try:
            # Mark all players as disconnected on startup
            self.db.mark_all_players_disconnected()

            # Load room data from database
            rooms_data = self.db.load_all_rooms()

            loaded_count = 0
            for room_data in rooms_data:
                try:
                    # Reconstruct Room object
                    room = self._reconstruct_room(room_data)

                    # Add to room manager
                    room_manager.rooms[room.room_id] = room

                    # Note: session_to_room mappings will be rebuilt as players reconnect

                    loaded_count += 1
                    logger.info("room_loaded",
                              room_id=room.room_id,
                              players=len(room.game_state.players),
                              phase=room.game_state.phase.value)

                except Exception as e:
                    logger.error("load_room_error",
                               room_id=room_data.get('room_id', 'unknown'),
                               error=str(e))
                    continue

            logger.info("rooms_loaded_from_database", count=loaded_count)
            return loaded_count

        except Exception as e:
            logger.error("load_all_rooms_error", error=str(e))
            return 0

    def _reconstruct_room(self, room_data: Dict[str, Any]) -> Room:
        """
        Reconstruct a Room object from persisted data.

        Args:
            room_data: Room data from database

        Returns:
            Reconstructed Room object
        """
        # Create room
        room = Room(room_id=room_data['room_id'])

        # Reconstruct game state
        game_state_dict = room_data.get('game_state')
        if game_state_dict:
            room.game_state = self._reconstruct_game_state(game_state_dict)
        else:
            # No game state saved, create fresh one
            room.game_state = GameState()

        # Add players to game state
        for player_data in room_data.get('players', []):
            player = self._reconstruct_player(player_data, room.game_state)

            # Ensure player is in game state if not already
            existing = room.game_state.get_player_by_id(player.id)
            if not existing:
                room.game_state.players.append(player)

            # Note: Don't map session_id yet - players need to reconnect
            # Mark as disconnected
            player.is_connected = False

        # Restore chat history
        room.chat_messages = room_data.get('chat_messages', [])

        return room

    def _reconstruct_game_state(self, game_state_dict: Dict[str, Any]) -> GameState:
        """
        Reconstruct GameState from dictionary.

        Args:
            game_state_dict: Game state dictionary

        Returns:
            Reconstructed GameState object
        """
        game_state = GameState()

        # Basic fields
        game_state.game_id = game_state_dict.get('game_id', game_state.game_id)
        game_state.phase = GamePhase(game_state_dict.get('phase', 'waiting'))
        game_state.dealer_position = game_state_dict.get('dealer_position', 0)
        game_state.current_turn = game_state_dict.get('current_turn', 0)
        game_state.declarer_position = game_state_dict.get('declarer_position')
        game_state.partner_position = game_state_dict.get('partner_position')
        game_state.partner_revealed = game_state_dict.get('partner_revealed', False)
        game_state.called_card_rank = game_state_dict.get('called_card_rank')
        game_state.trick_number = game_state_dict.get('trick_number', 0)
        game_state.trick_leader = game_state_dict.get('trick_leader')
        game_state.previous_trick_winner = game_state_dict.get('previous_trick_winner')

        # Lists
        game_state.players_who_discarded = game_state_dict.get('players_who_discarded', [])
        game_state.announcement_passes = game_state_dict.get('announcement_passes', [])

        # Reconstruct bid history
        game_state.bid_history = []
        for bid_dict in game_state_dict.get('bid_history', []):
            bid = Bid(
                player_position=bid_dict['player_position'],
                bid_type=BidType(bid_dict['bid_type'])
            )
            game_state.bid_history.append(bid)

        # Set winning bid if exists
        winning_bid_dict = game_state_dict.get('winning_bid')
        if winning_bid_dict:
            game_state.winning_bid = Bid(
                player_position=winning_bid_dict['player_position'],
                bid_type=BidType(winning_bid_dict['bid_type'])
            )

        # Reconstruct talon
        game_state.talon = [
            self._reconstruct_card(card_dict)
            for card_dict in game_state_dict.get('talon', [])
        ]

        # Reconstruct current trick
        game_state.current_trick = []
        for trick_card in game_state_dict.get('current_trick', []):
            player_pos = trick_card['player_position']
            card = self._reconstruct_card(trick_card['card'])
            game_state.current_trick.append((player_pos, card))

        # Reconstruct announcements
        game_state.announcements = []
        for ann_dict in game_state_dict.get('announcements', []):
            announcement = Announcement(
                player_position=ann_dict['player_position'],
                announcement_type=AnnouncementType(ann_dict['announcement_type']),
                announced=ann_dict['announced']
            )
            announcement.contra = ann_dict.get('contra', False)
            announcement.recontra = ann_dict.get('recontra', False)
            announcement.contra_by = ann_dict.get('contra_by')
            announcement.recontra_by = ann_dict.get('recontra_by')
            game_state.announcements.append(announcement)

        # Reconstruct announcement history
        game_state.announcement_history = []
        for ann_hist in game_state_dict.get('announcement_history', []):
            if ann_hist is None:
                game_state.announcement_history.append(None)
            else:
                announcement = Announcement(
                    player_position=ann_hist['player_position'],
                    announcement_type=AnnouncementType(ann_hist['announcement_type']),
                    announced=ann_hist['announced']
                )
                announcement.contra = ann_hist.get('contra', False)
                announcement.recontra = ann_hist.get('recontra', False)
                announcement.contra_by = ann_hist.get('contra_by')
                announcement.recontra_by = ann_hist.get('recontra_by')
                game_state.announcement_history.append(announcement)

        # Reconstruct trick history
        game_state.trick_history = game_state_dict.get('trick_history', [])

        # Note: Players are reconstructed separately and added to game_state.players

        return game_state

    def _reconstruct_player(self, player_data: Dict[str, Any], game_state: GameState) -> Player:
        """
        Reconstruct a Player object from persisted data.

        Args:
            player_data: Player data dictionary
            game_state: GameState to link player to

        Returns:
            Reconstructed Player object
        """
        # Try to find player in game state (already reconstructed from game_state_dict)
        existing_player = game_state.get_player_by_id(player_data['id'])

        if existing_player:
            # Update connection status from player_data
            existing_player.is_connected = player_data.get('is_connected', False)
            existing_player.is_ready = player_data.get('is_ready', False)
            return existing_player
        else:
            # Create new player (shouldn't happen normally)
            player = Player(
                name=player_data['name'],
                position=player_data['position']
            )
            player.id = player_data['id']
            player.is_connected = player_data.get('is_connected', False)
            player.is_ready = player_data.get('is_ready', False)
            return player

    def _reconstruct_card(self, card_dict: Dict[str, Any]) -> Card:
        """
        Reconstruct a Card object from dictionary.

        Args:
            card_dict: Card dictionary

        Returns:
            Reconstructed Card object
        """
        from models.card import Card
        return Card.from_dict(card_dict)

    async def delete_room(self, room_id: str) -> None:
        """
        Delete a room from persistence.

        Args:
            room_id: Room ID to delete
        """
        try:
            async with self._save_lock:
                self.db.delete_room(room_id)
                logger.info("room_deleted_from_persistence", room_id=room_id)
        except Exception as e:
            logger.error("delete_room_error", room_id=room_id, error=str(e))

    async def cleanup_old_rooms(self, days: int = 7) -> None:
        """
        Clean up old inactive rooms.

        Args:
            days: Delete rooms inactive for this many days
        """
        try:
            count = self.db.cleanup_old_rooms(days)
            if count > 0:
                logger.info("cleaned_up_old_rooms", count=count)
        except Exception as e:
            logger.error("cleanup_error", error=str(e))

    def close(self):
        """Close database connection."""
        self.db.close()
