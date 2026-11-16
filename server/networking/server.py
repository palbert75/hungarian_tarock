"""WebSocket server for Hungarian Tarokk.

Socket events are thin: they find the room and the player and call the
shared actions in `networking.actions`, which bots use as well.
"""

import asyncio
import time
from typing import Any, Optional, Tuple

import socketio
import structlog

from config import settings
from models.bid import BidType
from models.game_state import GamePhase
from models.player import Player
from networking.actions import GameService
from networking.limits import RateLimit, Refused, client_address
from networking.protocol import create_error_message
from networking.reports import ReportThrottle, build_report, may_return_to_reporter, save_report
from networking.room_manager import (
    BOT_DELAYS, EMPTY_TABLE_GRACE_SECONDS, STAND_IN_SECONDS, WAITING_GRACE_SECONDS, Room, RoomManager,
)

logger = structlog.get_logger()

# Create Socket.IO server
# Which web pages may connect: "*" for any, or the comma-separated list in CORS_ORIGINS
_origins = "*" if settings.cors_origins.strip() == "*" else [o.strip() for o in settings.cors_origins.split(",") if o.strip()]

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=_origins,
    logger=False,
    engineio_logger=False
)

# Room manager instance
room_manager = RoomManager()

# Persistence manager instance (will be initialized in init_persistence)
persistence_manager: Optional[Any] = None

# Limits per visitor: new tables per address, chat lines per player
new_table_limit = RateLimit(count=10, seconds=60)
chat_limit = RateLimit(count=5, seconds=5)
addresses: dict = {}  # sid -> address of the visitor

# How often abandoned tables and old database rows are swept away
SWEEP_SECONDS = 3600

# Set once the server is going down for a restart: from then on the tables stay as they were saved
shutting_down = False

# After a restart nobody is connected yet. A table is kept this long for its
# people to come back (their apps reconnect by themselves within seconds).
RESTART_GRACE_SECONDS = 600


async def auto_save_room(room: Room) -> None:
    """Auto-save room state to database."""
    if persistence_manager:
        await persistence_manager.save_room_complete(room)


def _load_strategy():
    """Use the rule-based bot strategy when it is available."""
    try:
        from bots.strategy import decide_for_seat
        return decide_for_seat
    except ImportError:
        return None


_strategy = _load_strategy()
def record_hand(room: Room, result: dict) -> None:
    """A hand is over: keep it for the statistics."""
    if persistence_manager:
        persistence_manager.record_hand(room, result)


def stats(days: int = 30) -> dict:
    """Played hands per day, and what is going on right now."""
    if not persistence_manager:
        raise RuntimeError("No database")
    result = persistence_manager.stats(days)
    tables = [room for room in room_manager.rooms.values() if any(p.is_connected for p in room.humans())]
    result["now"] = {
        "tables_with_people": len(tables),
        "people_connected": sum(1 for room in tables for p in room.humans() if p.is_connected),
        "tables_in_a_hand": sum(1 for room in tables
                                if room.game_state.phase not in (GamePhase.WAITING, GamePhase.GAME_END)),
    }
    return result


service = GameService(room_manager, sio.emit, save=auto_save_room, decide=_strategy, record_hand=record_hand)
service.hint = _strategy


# ---------------------------------------------------------------- helpers

async def send_error(sid: str, code: str, error: Exception) -> None:
    code = getattr(error, "code", code)  # a refusal names its own reason
    logger.error(code.lower(), sid=sid, error=str(error))
    await sio.emit("error", create_error_message(code, str(error)).to_dict(), room=sid)


def open_table(sid: str, player_name: str) -> Room:
    """A new table, unless this visitor opens too many or the server is full."""
    new_table_limit.check(addresses.get(sid, sid))
    if len(room_manager.rooms) >= settings.max_rooms:
        raise Refused("ROOMS_FULL", "The server is full, no new table can be opened now")
    return room_manager.create_room(sid, player_name)


async def sweep() -> int:
    """Close tables nobody sits at any more and drop old rows; returns the number of tables closed."""
    closed = 0
    now = time.time()
    for room in list(room_manager.rooms.values()):
        # People who dropped moments ago still count: their seat timer is running
        if room_manager._delete_if_no_humans(room, now):
            closed += 1
            if persistence_manager:
                await persistence_manager.delete_room(room.room_id)
    if persistence_manager:
        await persistence_manager.cleanup_old_rooms(settings.closed_room_keep_days)
    new_table_limit.prune()
    chat_limit.prune()
    if closed:
        logger.info("abandoned_tables_closed", count=closed)
    return closed


async def sweep_forever() -> None:
    while True:
        await asyncio.sleep(SWEEP_SECONDS)
        try:
            await sweep()
        except Exception as e:
            logger.error("sweep_error", error=str(e))


def seat_of(sid: str) -> Tuple[Room, Player]:
    """Room and player for a socket, or ValueError."""
    room = room_manager.get_room_by_session(sid)
    if not room:
        raise ValueError("Not in a room")
    player = room.get_player_by_session(sid)
    if not player:
        raise ValueError("Player not found")
    return room, player


def owner_seat_of(sid: str) -> Tuple[Room, Player]:
    room, player = seat_of(sid)
    if not room.is_owner(player.id):
        raise PermissionError("Only the table owner can do that")
    return room, player


async def stand_in_absent(room: Room) -> None:
    """Let a bot play for whoever has been away too long while others are waiting."""
    if not room.stand_in_absent(time.time()):
        return
    await service.broadcast_room_state(room)
    await service.broadcast_game_state(room)
    if room.can_start_next_hand():
        await service.start_next_hand(room)
    else:
        await auto_save_room(room)
        service.schedule_bot(room)


async def stand_in_later(room_id: str, delay: float = STAND_IN_SECONDS) -> None:
    await asyncio.sleep(delay)
    room = room_manager.get_room(room_id)
    if room:
        await stand_in_absent(room)


async def hold_seat_then_free(room_id: str, player_id: str, grace: float = WAITING_GRACE_SECONDS) -> None:
    """A dropped player's seat is held for a while; a table left with nobody is closed."""
    await asyncio.sleep(grace)
    if not room_manager.get_room(room_id):
        return
    await stand_in_absent(room_manager.get_room(room_id))
    room = room_manager.expire_seat(room_id, player_id, now=time.time())
    if room and grace < EMPTY_TABLE_GRACE_SECONDS:
        player = room.game_state.get_player_by_id(player_id)
        if player and not player.vacant and not player.is_connected:
            # The last person of the table: the seat and the table wait longer
            await asyncio.sleep(EMPTY_TABLE_GRACE_SECONDS - grace)
            if not room_manager.get_room(room_id):
                return
            room = room_manager.expire_seat(room_id, player_id, now=time.time())
    if room:
        await service.broadcast_room_state(room)
        if room.game_state.phase != GamePhase.WAITING:
            await service.broadcast_game_state(room)
        await auto_save_room(room)
    elif persistence_manager:
        await persistence_manager.delete_room(room_id)


# ------------------------------------------------------------- connection

@sio.event
async def connect(sid: str, environ: dict):
    """Handle client connection."""
    addresses[sid] = client_address(environ)
    logger.info("client_connected", sid=sid, address=addresses[sid])


@sio.event
async def disconnect(sid: str):
    """A socket dropped: the player keeps the seat and may come back."""
    logger.info("client_disconnected", sid=sid)
    addresses.pop(sid, None)
    if shutting_down:
        # The server closes the connections itself; everybody keeps seat and table ownership
        return
    room, player = room_manager.disconnect_session(sid)
    if not room or not player:
        return

    await service.announce_connection(room, player, connected=False)
    await service.broadcast_room_state(room)
    if room.game_state.phase != GamePhase.WAITING:
        await service.broadcast_game_state(room)
    asyncio.create_task(hold_seat_then_free(room.room_id, player.id))
    asyncio.create_task(stand_in_later(room.room_id))
    await auto_save_room(room)


# ------------------------------------------------------------ lobby / room

@sio.event
async def list_rooms(sid: str, data: dict):
    """Handle list rooms request."""
    try:
        await sio.emit("rooms_list", {"rooms": room_manager.get_available_rooms()}, room=sid)
    except Exception as e:
        await send_error(sid, "LIST_ROOMS_ERROR", e)


async def _after_join(sid: str, room: Room, player: Player, was_away: bool) -> None:
    await sio.enter_room(sid, room.room_id)
    await sio.emit("joined", {
        "room_id": room.room_id,
        "player_id": player.id,
        "position": player.position,
    }, room=sid)

    chat_history = room.get_chat_history()
    if chat_history:
        await sio.emit("chat_history", {"messages": chat_history}, room=sid)

    if was_away:
        await service.announce_connection(room, player, connected=True)

    await service.broadcast_room_state(room)

    if room.game_state.phase != GamePhase.WAITING:
        await service.broadcast_game_state(room)
        if room.game_state.phase == GamePhase.GAME_END and room.last_game_over:
            await sio.emit("game_over", {"type": "game_over", "data": room.last_game_over}, room=sid)
        await service.send_your_turn(room, only_session=sid)

    await auto_save_room(room)
    if was_away:
        # Somebody is here again to play with: others who are still away get their stand-in
        await stand_in_absent(room)


@sio.event
async def create_room(sid: str, data: dict):
    """Create a table; the creator owns it."""
    try:
        player_name = (data or {}).get("player_name") or "Player"
        room = open_table(sid, player_name)
        player = room.get_player_by_session(sid)
        await _after_join(sid, room, player, was_away=False)
    except Exception as e:
        await send_error(sid, "CREATE_ROOM_ERROR", e)


@sio.event
async def join_room(sid: str, data: dict):
    """Join a table, or come back to a seat already held there."""
    try:
        room_id = data.get("room_id")
        player_name = data.get("player_name") or "Player"
        player_id = data.get("player_id")

        if not room_id:
            room = open_table(sid, player_name)
            player = room.get_player_by_session(sid)
            was_away = False
        else:
            room, player, was_away = room_manager.join_room(room_id, sid, player_name, player_id)

        await _after_join(sid, room, player, was_away)
    except Exception as e:
        await send_error(sid, "JOIN_ROOM_ERROR", e)


@sio.event
async def ready(sid: str, data: dict):
    """Handle player ready status."""
    try:
        room, player = seat_of(sid)
        room.set_player_ready(player.id, (data or {}).get("ready", True))
        await service.broadcast_room_state(room)
        if room.can_start_game():
            await service.start_game(room)
        else:
            await auto_save_room(room)
    except Exception as e:
        await send_error(sid, "READY_ERROR", e)


@sio.event
async def next_hand(sid: str, data: dict):
    """A player asks for the next hand; it is dealt when every person has."""
    try:
        room, player = seat_of(sid)
        if room.game_state.phase != GamePhase.GAME_END:
            raise ValueError("The hand is not over")
        player.ready_next = True
        await service.broadcast_room_state(room)
        if room.can_start_next_hand():
            await service.start_next_hand(room)
        else:
            await auto_save_room(room)
    except Exception as e:
        await send_error(sid, "NEXT_HAND_ERROR", e)


@sio.event
async def leave_room(sid: str, data: dict):
    """A player leaves on purpose."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            return
        player = room.get_player_by_session(sid)
        room_id = room.room_id
        mid_game = not room.can_change_seats()

        remaining = room_manager.leave_room(sid)
        await sio.leave_room(sid, room_id)

        if remaining:
            if player and mid_game:
                await service.announce_connection(remaining, player, connected=False)
            await service.broadcast_room_state(remaining)
            if remaining.game_state.phase != GamePhase.WAITING:
                await service.broadcast_game_state(remaining)
            await service.maybe_start(remaining)
            await auto_save_room(remaining)
        elif persistence_manager:
            await persistence_manager.delete_room(room_id)
    except Exception as e:
        await send_error(sid, "LEAVE_ROOM_ERROR", e)


# -------------------------------------------------------- table owner only

async def _owner_action(sid: str, code: str, change) -> None:
    """Run a seat change by the table owner and tell the table."""
    try:
        room, _ = owner_seat_of(sid)
        change(room)
        await service.broadcast_room_state(room)
        if room.game_state.phase != GamePhase.WAITING:
            await service.broadcast_game_state(room)
        await service.maybe_start(room)
        await auto_save_room(room)
    except PermissionError as e:
        await send_error(sid, "NOT_OWNER", e)
    except Exception as e:
        await send_error(sid, code, e)


@sio.event
async def swap_seats(sid: str, data: dict):
    await _owner_action(sid, "SEAT_ERROR",
                        lambda room: room.swap_seats(int(data["from_position"]), int(data["to_position"])))


@sio.event
async def add_bot(sid: str, data: dict):
    position = (data or {}).get("position")
    await _owner_action(sid, "BOT_ERROR",
                        lambda room: room.add_bot(None if position is None else int(position)))


@sio.event
async def remove_bot(sid: str, data: dict):
    await _owner_action(sid, "BOT_ERROR", lambda room: room.remove_bot(int(data["position"])))


@sio.event
async def fill_bots(sid: str, data: dict):
    await _owner_action(sid, "BOT_ERROR", lambda room: room.fill_bots())


@sio.event
async def set_bot_speed(sid: str, data: dict):
    def change(room: Room) -> None:
        speed = data.get("speed")
        if speed not in BOT_DELAYS:
            raise ValueError("Unknown speed")
        room.bot_speed = speed

    await _owner_action(sid, "BOT_ERROR", change)


@sio.event
async def replace_with_bot(sid: str, data: dict):
    """Mid-game: let a bot play a disconnected player's seat (the player may return)."""
    try:
        room, _ = owner_seat_of(sid)
        if room.can_change_seats():
            raise ValueError("Use add bot before the game or between hands")
        player = room.replace_with_bot(int(data["position"]))
        await service.announce_connection(room, player, connected=False)
        await service.broadcast_room_state(room)
        await service.broadcast_game_state(room)
        await auto_save_room(room)
        service.schedule_bot(room)
    except PermissionError as e:
        await send_error(sid, "NOT_OWNER", e)
    except Exception as e:
        await send_error(sid, "BOT_ERROR", e)


# ------------------------------------------------------------ game actions

@sio.event
async def place_bid(sid: str, data: dict):
    try:
        room, player = seat_of(sid)
        await service.act_bid(room, player, BidType(data.get("bid_type")))
    except Exception as e:
        await send_error(sid, "BID_ERROR", e)


@sio.event
async def discard_cards(sid: str, data: dict):
    try:
        room, player = seat_of(sid)
        await service.act_discard(room, player, data.get("card_ids", []))
    except Exception as e:
        await send_error(sid, "DISCARD_ERROR", e)


@sio.event
async def call_partner(sid: str, data: dict):
    try:
        room, player = seat_of(sid)
        await service.act_call_partner(room, player, data.get("tarokk_rank"))
    except Exception as e:
        await send_error(sid, "CALL_PARTNER_ERROR", e)


@sio.event
async def make_announcement(sid: str, data: dict):
    """Make one or several announcements in one turn."""
    try:
        room, player = seat_of(sid)
        types = data.get("announcement_types")
        if types is None:
            single = data.get("announcement_type")
            types = [single] if single else []
        await service.act_announce(room, player, types, data.get("announced", True))
    except Exception as e:
        await send_error(sid, "ANNOUNCEMENT_ERROR", e)


@sio.event
async def pass_announcement(sid: str, data: dict):
    try:
        room, player = seat_of(sid)
        await service.act_pass_announcement(room, player)
    except Exception as e:
        await send_error(sid, "PASS_ANNOUNCEMENT_ERROR", e)


@sio.event
async def contra_announcement(sid: str, data: dict):
    try:
        room, player = seat_of(sid)
        await service.act_contra(room, player, data.get("announcement_type"))
    except Exception as e:
        await send_error(sid, "CONTRA_ERROR", e)


@sio.event
async def recontra_announcement(sid: str, data: dict):
    try:
        room, player = seat_of(sid)
        await service.act_recontra(room, player, data.get("announcement_type"))
    except Exception as e:
        await send_error(sid, "RECONTRA_ERROR", e)


@sio.event
async def play_card(sid: str, data: dict):
    try:
        room, player = seat_of(sid)
        await service.act_play_card(room, player, data.get("card_id"))
    except Exception as e:
        await send_error(sid, "PLAY_CARD_ERROR", e)


# -------------------------------------------------------------------- chat

@sio.event
async def send_chat_message(sid: str, data: dict):
    """Handle chat message from player."""
    try:
        room, player = seat_of(sid)
        chat_limit.check(player.id)

        message = (data.get("message") or "").strip()
        if not message:
            raise ValueError("Message cannot be empty")
        if len(message) > 500:
            raise ValueError("Message too long (max 500 characters)")

        now = int(time.time() * 1000)
        chat_message = {
            "id": f"{player.id}_{now}",
            "player_name": player.name,
            "message": message,
            "timestamp": now,
        }
        room.add_chat_message(chat_message)
        if persistence_manager:
            persistence_manager.save_chat_message(room.room_id, chat_message)
        await sio.emit("chat_message", chat_message, room=room.room_id)
    except Exception as e:
        await send_error(sid, "CHAT_ERROR", e)


# ----------------------------------------------------------------- reports

report_throttle = ReportThrottle()


@sio.event
async def report_problem(sid: str, data: dict):
    """A player describes a problem; the whole table is stored with it for later analysis."""
    try:
        room, player = seat_of(sid)
        report_throttle.check(player.id)
        report = build_report(room, player, data.get("text"), data.get("client"))
        path = save_report(report)
        logger.info("problem_reported", report_id=report["id"], room_id=room.room_id, path=str(path))
        reply = {"id": report["id"]}
        # The report shows every hand: only hand it back when that cannot help anyone cheat
        if may_return_to_reporter(room, player):
            reply["report"] = report
        await sio.emit("report_saved", reply, room=sid)
    except Exception as e:
        await send_error(sid, "REPORT_ERROR", e)


# ------------------------------------------------------------- persistence

async def init_persistence(db_path: str = "data/tarokk_game.db"):
    """Initialize persistence system and load persisted rooms."""
    global persistence_manager

    try:
        from persistence.persistence_manager import PersistenceManager

        persistence_manager = PersistenceManager(db_path)
        logger.info("persistence_initialized", db_path=db_path)

        loaded_count = await persistence_manager.load_all_rooms(room_manager)
        logger.info("rooms_loaded_on_startup", count=loaded_count)

        now = time.time()
        for room in list(room_manager.rooms.values()):
            # Nobody is connected yet: hold every seat as if its player had just dropped
            for player in room.humans():
                if not player.is_connected:
                    room.dropped_at[player.id] = now + RESTART_GRACE_SECONDS - EMPTY_TABLE_GRACE_SECONDS
                    asyncio.create_task(hold_seat_then_free(room.room_id, player.id, RESTART_GRACE_SECONDS))
            # A bot may be the one to move in a restored game
            service.schedule_bot(room)

        await persistence_manager.cleanup_old_rooms(settings.closed_room_keep_days)
        asyncio.create_task(sweep_forever())

        return persistence_manager

    except Exception as e:
        logger.error("persistence_init_error", error=str(e))
        return None


async def announce_restart() -> None:
    """Before the connections are closed for a restart: tell the players, save every table."""
    global shutting_down
    shutting_down = True
    try:
        await sio.emit("server_restarting", {})
        if persistence_manager:
            for room in list(room_manager.rooms.values()):
                await persistence_manager.save_room_complete(room)
        logger.info("restart_announced", rooms=len(room_manager.rooms))
        # Let the notice leave before the sockets are closed
        await asyncio.sleep(0.3)
    except Exception as e:
        logger.error("restart_announce_error", error=str(e))


async def shutdown_persistence():
    """Shutdown persistence system and save all rooms."""
    global persistence_manager

    if persistence_manager:
        try:
            for room_id, room in room_manager.rooms.items():
                await persistence_manager.save_room_complete(room)
                logger.info("room_saved_on_shutdown", room_id=room_id)

            persistence_manager.close()
            logger.info("persistence_shutdown_complete")

        except Exception as e:
            logger.error("persistence_shutdown_error", error=str(e))


# Export the Socket.IO app
app = socketio.ASGIApp(sio)
