"""The shape of a bot decision, and a rule-free fallback that is always legal."""

from dataclasses import dataclass, field
from typing import Dict, Any

from models.card import TarokkRank
from models.game_state import GameState, GamePhase
from validation.rules import get_legal_cards

# Tarokk ranks from the XX downwards (candidates for the partner call)
CALL_ORDER = [
    TarokkRank.XX.value, TarokkRank.XIX.value, TarokkRank.XVIII.value,
    TarokkRank.XVII.value, TarokkRank.XVI.value, TarokkRank.XV.value,
    TarokkRank.XIV.value, TarokkRank.XIII.value, TarokkRank.XII.value,
]


@dataclass
class Decision:
    """
    What a seat should do now, and why.

    action: bid | discard | call_partner | announce | pass_announcement | contra | play_card
    payload: the action's arguments
    reason_key / reason_params: a translatable explanation (used for hints)
    """
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    reason_key: str = ""
    reason_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "payload": self.payload,
            "reason_key": self.reason_key,
            "reason_params": self.reason_params,
        }


def fallback_decision(game_state: GameState, position: int) -> Decision:
    """A legal action without any strategy. Used if the strategy fails."""
    player = game_state.get_player(position)
    phase = game_state.phase

    if phase == GamePhase.BIDDING:
        return Decision("bid", {"bid_type": "pass"}, "hint.fallback")

    if phase == GamePhase.DISCARDING:
        count = player.get_hand_size() - 9
        candidates = [c for c in player.hand if c.can_be_discarded()]
        candidates.sort(key=lambda c: (c.is_tarokk(), c.tarokk_value(), c.points))
        return Decision("discard", {"card_ids": [c.id for c in candidates[:count]]}, "hint.fallback")

    if phase == GamePhase.PARTNER_CALL:
        held = {c.rank for c in player.hand if c.is_tarokk()}
        rank = next((r for r in CALL_ORDER if r not in held), TarokkRank.XX.value)
        return Decision("call_partner", {"tarokk_rank": rank}, "hint.fallback")

    if phase == GamePhase.ANNOUNCEMENTS:
        return Decision("pass_announcement", {}, "hint.fallback")

    if phase == GamePhase.PLAYING:
        is_first = len(game_state.current_trick) == 0
        lead_suit = None if is_first else game_state.current_trick[0][1].suit
        legal = get_legal_cards(player.hand, lead_suit, is_first)
        return Decision("play_card", {"card_id": legal[0].id}, "hint.fallback")

    raise ValueError(f"No action in phase {phase.value}")
