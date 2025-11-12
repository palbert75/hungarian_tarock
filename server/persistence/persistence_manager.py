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
            logger.info("persistence_load_starting")

            # Mark all players as disconnected on startup
            self.db.mark_all_players_disconnected()
            logger.info("marked_all_players_disconnected")

            # Load room data from database
            rooms_data = self.db.load_all_rooms()
            logger.info("database_rooms_found", count=len(rooms_data))

            loaded_count = 0
            for room_data in rooms_data:
                try:
                    room_id = room_data.get('room_id', 'unknown')
                    logger.info("loading_room",
                               room_id=room_id,
                               players_count=len(room_data.get('players', [])),
                               has_game_state=room_data.get('game_state') is not None,
                               chat_messages=len(room_data.get('chat_messages', [])))

                    # Reconstruct Room object
                    room = self._reconstruct_room(room_data)

                    # Log reconstructed room details
                    player_details = [
                        {
                            'name': p.name,
                            'position': p.position,
                            'hand_size': len(p.hand),
                            'tricks_won': len(p.tricks_won),
                            'discards': len(p.discard_pile)
                        }
                        for p in room.game_state.players
                    ]

                    logger.info("room_reconstructed",
                              room_id=room.room_id,
                              phase=room.game_state.phase.value,
                              trick_number=room.game_state.trick_number,
                              current_turn=room.game_state.current_turn,
                              players=player_details,
                              talon_size=len(room.game_state.talon),
                              current_trick_size=len(room.game_state.current_trick),
                              bid_history_size=len(room.game_state.bid_history))

                    # Add to room manager
                    room_manager.rooms[room.room_id] = room

                    # Note: session_to_room mappings will be rebuilt as players reconnect

                    loaded_count += 1
                    logger.info("room_loaded_successfully",
                              room_id=room.room_id,
                              players=len(room.game_state.players),
                              phase=room.game_state.phase.value)

                except Exception as e:
                    logger.error("load_room_error",
                               room_id=room_data.get('room_id', 'unknown'),
                               error=str(e),
                               error_type=type(e).__name__,
                               traceback=True)
                    import traceback
                    logger.error("load_room_traceback",
                               traceback=traceback.format_exc())
                    continue

            logger.info("persistence_load_complete",
                       rooms_loaded=loaded_count,
                       rooms_in_database=len(rooms_data))
            return loaded_count

        except Exception as e:
            logger.error("load_all_rooms_error",
                        error=str(e),
                        error_type=type(e).__name__)
            import traceback
            logger.error("load_all_rooms_traceback",
                        traceback=traceback.format_exc())
            return 0

    def _reconstruct_room(self, room_data: Dict[str, Any]) -> Room:
        """
        Reconstruct a Room object from persisted data.

        Args:
            room_data: Room data from database

        Returns:
            Reconstructed Room object
        """
        room_id = room_data['room_id']
        logger.debug("reconstructing_room", room_id=room_id)

        # Create room
        room = Room(room_id=room_id)

        # Reconstruct game state (includes players with all their cards)
        game_state_dict = room_data.get('game_state')
        if game_state_dict:
            logger.debug("reconstructing_game_state",
                        room_id=room_id,
                        phase=game_state_dict.get('phase'),
                        players_in_json=len(game_state_dict.get('players', [])))
            room.game_state = self._reconstruct_game_state(game_state_dict)
            logger.debug("game_state_reconstructed",
                        room_id=room_id,
                        players_loaded=len(room.game_state.players))
        else:
            # No game state saved, create fresh one
            logger.warning("no_game_state_in_database", room_id=room_id)
            room.game_state = GameState()

        # Update player connection status from players table (all disconnected after restart)
        for player_data in room_data.get('players', []):
            player = room.game_state.get_player_by_id(player_data['id'])
            if player:
                # Update connection status (should be False after restart)
                player.is_connected = False
                player.is_ready = player_data.get('is_ready', False)
                logger.debug("player_connection_updated",
                           room_id=room_id,
                           player_id=player_data['id'],
                           player_name=player.name,
                           is_ready=player.is_ready)

        # Restore chat history
        room.chat_messages = room_data.get('chat_messages', [])
        logger.debug("chat_history_restored",
                    room_id=room_id,
                    message_count=len(room.chat_messages))

        return room

    def _reconstruct_game_state(self, game_state_dict: Dict[str, Any]) -> GameState:
        """
        Reconstruct GameState from dictionary.

        Args:
            game_state_dict: Game state dictionary

        Returns:
            Reconstructed GameState object
        """
        logger.debug("reconstructing_game_state_start",
                    game_id=game_state_dict.get('game_id'),
                    phase=game_state_dict.get('phase'))

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

        logger.debug("game_state_basic_fields_set",
                    phase=game_state.phase.value,
                    trick_number=game_state.trick_number,
                    current_turn=game_state.current_turn,
                    declarer=game_state.declarer_position,
                    partner=game_state.partner_position)

        # Lists
        game_state.players_who_discarded = game_state_dict.get('players_who_discarded', [])

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
        logger.debug("trick_history_loaded", tricks=len(game_state.trick_history))

        # Reconstruct players with their cards
        logger.debug("reconstructing_players",
                    player_count=len(game_state_dict.get('players', [])))

        game_state.players = []
        for idx, player_dict in enumerate(game_state_dict.get('players', [])):
            logger.debug("reconstructing_player",
                        player_index=idx,
                        player_id=player_dict.get('id'),
                        player_name=player_dict.get('name'),
                        position=player_dict.get('position'),
                        hand_cards_in_dict=len(player_dict.get('hand', [])),
                        tricks_cards_in_dict=len(player_dict.get('tricks_won', [])),
                        discard_cards_in_dict=len(player_dict.get('discard_pile', [])))

            # Reconstruct hand
            hand = [self._reconstruct_card(card_dict) for card_dict in player_dict.get('hand', [])]
            logger.debug("player_hand_reconstructed",
                        player_name=player_dict['name'],
                        hand_size=len(hand),
                        first_card=hand[0].rank if hand else None)

            # Reconstruct tricks_won
            tricks_won = [self._reconstruct_card(card_dict) for card_dict in player_dict.get('tricks_won', [])]

            # Reconstruct discard_pile
            discard_pile = [self._reconstruct_card(card_dict) for card_dict in player_dict.get('discard_pile', [])]

            # Create player
            player = Player(
                name=player_dict['name'],
                position=player_dict['position'],
                hand=hand,
                tricks_won=tricks_won,
                discard_pile=discard_pile,
                is_connected=player_dict.get('is_connected', False),
                is_ready=player_dict.get('is_ready', False),
                is_declarer=player_dict.get('is_declarer', False),
                is_partner=player_dict.get('is_partner', False),
                partner_revealed=player_dict.get('partner_revealed', False)
            )
            player.id = player_dict['id']
            game_state.players.append(player)

            logger.debug("player_reconstructed",
                        player_id=player.id,
                        player_name=player.name,
                        position=player.position,
                        hand_size=len(player.hand),
                        tricks_won_size=len(player.tricks_won),
                        discard_pile_size=len(player.discard_pile),
                        is_declarer=player.is_declarer,
                        is_partner=player.is_partner)

        logger.debug("all_players_reconstructed", total_players=len(game_state.players))

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
