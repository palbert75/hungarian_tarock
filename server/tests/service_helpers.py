"""Helpers for driving the game through GameService without sockets."""

import random
from typing import List, Tuple

from networking.actions import GameService
from networking.room_manager import Room, RoomManager


class Recorder:
    """Stands in for sio.emit and remembers what was sent."""

    def __init__(self):
        self.events: List[Tuple[str, dict, str]] = []

    async def __call__(self, event, data=None, room=None, **kwargs):
        self.events.append((event, data, room))

    def names(self) -> List[str]:
        return [e[0] for e in self.events]

    def of(self, name: str) -> List[dict]:
        return [e[1] for e in self.events if e[0] == name]

    def clear(self) -> None:
        self.events.clear()


def make_service(decide=None) -> Tuple[GameService, RoomManager, Recorder]:
    manager = RoomManager()
    recorder = Recorder()
    service = GameService(manager, recorder, decide=decide)
    service.redeal_pause = 0
    service.trick_pause = 0
    service.auto_bots = False
    return service, manager, recorder


def table_of_four(manager: RoomManager, names=("Anna", "Bela", "Csaba", "Dora")) -> Room:
    """A room with four people, all ready. Session ids are 's0'..'s3'."""
    room = manager.create_room("s0", names[0])
    for i, name in enumerate(names[1:], start=1):
        manager.join_room(room.room_id, f"s{i}", name)
    for p in room.players:
        p.is_ready = True
    return room


async def play_out_with_fallback(service: GameService, room: Room, max_actions: int = 300) -> int:
    """Play the current hand to the end with every seat using the service's decide function."""
    from models.game_state import GamePhase

    done = 0
    while room.game_state.phase != GamePhase.GAME_END and done < max_actions:
        position = service.turn_position(room)
        player = room.game_state.get_player(position)
        decision = service.decide(room.game_state, position)
        await service.apply_decision(room, player, decision)
        done += 1
    return done


def seed(n: int) -> None:
    random.seed(n)
