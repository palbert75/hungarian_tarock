"""
Rule-based play for bots, and the same advice as tutorial hints.

Every function takes a SeatView (only what that seat may see) and returns a
Decision with a translatable reason. The rules come from the design document,
sections 5.2 (the owner's rules) and 5.3 (kept deliberately simple).
"""

from typing import List, Optional

import structlog

from bots.counting import PAGAT, SKIZ, XXI, observed_voids, skiz_out, tarokks_out, xxi_played
from bots.decision import CALL_ORDER, Decision, fallback_decision
from bots.view import Play, SeatView, build_view
from models.card import Card, Suit
from models.game_state import GameState, GamePhase

logger = structlog.get_logger()

BID_LEVEL = {"three": 1, "two": 2, "one": 3, "solo": 4}

# Tactics beyond the owner's rules, each kept because it helped (or did no harm and
# follows from the table's conventions) when the same 3000 deals were played with
# and without it: see tools/ab_tactics.py. Tried and dropped: playing tarokk back
# to a partner in general, small-tarokk leads from any long hand, winning every
# late trick, drawing tarokks after the four-kings signal, holding the skíz back.
ADOPTED = frozenset({
    "voids",           # lead suits a teammate cannot follow, avoid those an opponent cannot
    "stop_foe",        # take a trick a known opponent is winning
    "safe_feed",       # give points only to a trick that is certain
    "ulti_small",      # pagát ulti announcer draws tarokks with small ones
    "ulti_support",    # the announcer's teammate leads tarokks too
    "signal_partner",  # four kings from a non-declarer shows the table who the partner is
    "signal_double",   # the declarer answers that signal with double game when strong
    "xx_cheap_skart",  # a non-declarer holding the XX discards cheap cards
})
TACTICS: set = set(ADOPTED)

# Pagát ulti: nine tarokks, or eight when three of them are XVII or higher
ULTI_SURE_TAROKKS = 9
ULTI_MIN_TAROKKS = 8
ULTI_MIN_HIGH = 3
# Tarokks needed (with all three honours) before a bot announces trull
TRULL_MIN_TAROKKS = 7


# ------------------------------------------------------------------ bidding

def _next_bid(view: SeatView) -> Optional[str]:
    """The cheapest way to stay in the auction: hold if allowed, else the lowest legal bid."""
    if "hold" in view.valid_bids:
        return "hold"
    real = [b for b in view.valid_bids if b in BID_LEVEL]
    return min(real, key=lambda b: BID_LEVEL[b]) if real else None


def _level_of(view: SeatView, bid: str) -> int:
    if bid == "hold":
        return BID_LEVEL.get(view.highest_bid or "", 0)
    return BID_LEVEL[bid]


def decide_bid(view: SeatView) -> Decision:
    def pass_(key: str, **params) -> Decision:
        return Decision("bid", {"bid_type": "pass"}, key, params)

    tarokk_count = len(view.tarokks)
    has_skiz, has_xxi, has_pagat = view.holds("skiz"), view.holds("XXI"), view.holds("I")
    if not (has_skiz or has_xxi or has_pagat):
        return pass_("hint.bid.no_honour")

    bid = _next_bid(view)
    if bid is None:
        return pass_("hint.bid.nothing_left")
    level = _level_of(view, bid)

    if has_xxi:
        # Always bid with the XXI, up to "one"; never solo
        if level > BID_LEVEL["one"]:
            return pass_("hint.bid.xxi_stop_solo")
        return Decision("bid", {"bid_type": bid}, "hint.bid.xxi_always", {"bid": bid})

    if has_skiz:
        others = tarokk_count - 1
        if others >= 4:
            return pass_("hint.bid.skiz_strong_pass", count=others)
        if level > BID_LEVEL["two"]:
            return pass_("hint.bid.limit_reached", bid=view.highest_bid)
        return Decision("bid", {"bid_type": bid}, "hint.bid.skiz_weak_bid", {"bid": bid, "count": others})

    # Only the pagát
    if tarokk_count < 8:
        return pass_("hint.bid.pagat_few_tarokks", count=tarokk_count)
    if level > BID_LEVEL["two"]:
        return pass_("hint.bid.limit_reached", bid=view.highest_bid)
    return Decision("bid", {"bid_type": bid}, "hint.bid.pagat_many_tarokks", {"bid": bid, "count": tarokk_count})


# -------------------------------------------------------------------- skart

def decide_discard(view: SeatView) -> Decision:
    count = view.discard_count
    allowed = [c for c in view.hand if c.can_be_discarded()]
    suit_cards = [c for c in allowed if not c.is_tarokk()]
    tarokks = sorted((c for c in allowed if c.is_tarokk()), key=lambda c: c.tarokk_value())

    # Whoever holds the XX will most likely be called: their skart counts for the other side
    cheap_first = ("xx_cheap_skart" in TACTICS and view.position != view.declarer_position and view.holds("XX"))

    def suit_order(card: Card):
        in_suit = [c for c in view.hand if c.suit == card.suit]
        has_king = any(c.is_king() for c in in_suit)
        # Suits without a king first, shortest first; inside a suit the dearest card first
        return (has_king, len(in_suit), card.suit.value, card.points if cheap_first else -card.points)

    ordered = sorted(suit_cards, key=suit_order) + tarokks
    chosen = ordered[:count]
    key = "hint.discard.with_tarokks" if any(c.is_tarokk() for c in chosen) else "hint.discard.suits"
    return Decision("discard", {"card_ids": [c.id for c in chosen]}, key, {"cards": [c.id for c in chosen]})


# ------------------------------------------------------------- partner call

def decide_call(view: SeatView) -> Decision:
    held = {c.rank for c in view.tarokks}
    rank = next((r for r in CALL_ORDER if r not in held), CALL_ORDER[0])
    key = "hint.call.xx" if rank == CALL_ORDER[0] else "hint.call.lower"
    return Decision("call_partner", {"tarokk_rank": rank}, key, {"rank": rank})


# ------------------------------------------------------------ announcements

def _signal_seat(view: SeatView) -> Optional[int]:
    """The seat that announced four kings: by the table's convention the caller's partner, long in tarokks."""
    for a in view.announcements:
        if a.announcement_type.value == "four_kings" and a.player_position != view.declarer_position:
            return a.player_position
    return None


def decide_announcement(view: SeatView) -> Decision:
    valid = set(view.valid_announcements)
    tarokk_count = len(view.tarokks)
    high = len([c for c in view.tarokks if c.tarokk_value() > 13])
    wanted = []  # (type, reason key, params)

    if view.i_am_partner:
        if tarokk_count >= 6:
            wanted.append(("four_kings", "hint.announce.four_kings", {"count": tarokk_count}))
        if high >= 5:
            wanted.append(("double_game", "hint.announce.double_game", {"count": high}))
    if view.holds("skiz") and view.holds("XXI") and view.holds("I") and tarokk_count >= TRULL_MIN_TAROKKS:
        wanted.append(("trull", "hint.announce.trull", {}))
    top = len([c for c in view.tarokks if c.tarokk_value() >= 17])
    ulti_hand = tarokk_count >= ULTI_SURE_TAROKKS or (tarokk_count >= ULTI_MIN_TAROKKS and top >= ULTI_MIN_HIGH)
    if view.holds("I") and ulti_hand:
        wanted.append(("pagat_ultimo", "hint.announce.pagat_ultimo", {"count": tarokk_count}))

    if ("signal_double" in TACTICS and view.position == view.declarer_position and tarokk_count >= 6
            and (view.holds("skiz") or view.holds("XXI")) and _signal_seat(view) is not None):
        wanted.append(("double_game", "hint.announce.double_after_signal", {"count": tarokk_count}))

    wanted = [w for w in wanted if w[0] in valid]
    if not wanted:
        return Decision("pass_announcement", {}, "hint.announce.pass")
    types = [w[0] for w in wanted]
    if len(wanted) == 1:
        return Decision("announce", {"announcement_types": types}, wanted[0][1], wanted[0][2])
    return Decision("announce", {"announcement_types": types}, "hint.announce.several",
                    {"announcement": types[0], "count": len(types)})


# ---------------------------------------------------------------- card play

def _winning_play(trick: List[Play]) -> Play:
    tarokk_plays = [p for p in trick if p[1].is_tarokk()]
    if tarokk_plays:
        return max(tarokk_plays, key=lambda p: p[1].tarokk_value())
    lead = trick[0][1].suit
    return max((p for p in trick if p[1].suit == lead), key=lambda p: p[1].suit_rank_value())


def _beats(card: Card, trick: List[Play]) -> bool:
    best = _winning_play(trick)[1]
    if card.is_tarokk():
        return not best.is_tarokk() or card.tarokk_value() > best.tarokk_value()
    if best.is_tarokk():
        return False
    return card.suit == trick[0][1].suit and card.suit_rank_value() > best.suit_rank_value()


def _is(card: Card, value: int) -> bool:
    return card.is_tarokk() and card.tarokk_value() == value


def _cheapness(card: Card):
    """Sort key: what I would give away first."""
    if card.is_tarokk():
        # The pagát is worth five points: last among the tarokks to throw away
        return (1, 30 if _is(card, PAGAT) else card.tarokk_value())
    return (0, card.points)


def _announced(view: SeatView, kind: str, by_me: Optional[bool] = None) -> bool:
    for a in view.announcements:
        if a.announcement_type.value != kind:
            continue
        if by_me is None or (a.player_position == view.position) == by_me:
            return True
    return False


def _longest_suit_low(cards: List[Card], view: Optional[SeatView] = None) -> Optional[Card]:
    suit_cards = [c for c in cards if not c.is_tarokk()]
    if not suit_cards:
        return None
    length = {s: len([c for c in suit_cards if c.suit == s]) for s in Suit}
    voids = observed_voids(view) if view is not None and "voids" in TACTICS else set()

    def key(c: Card):
        mate_void = any((seat, c.suit) in voids for seat in view.teammates()) if voids else False
        foes_void = sum((seat, c.suit) in voids for seat in view.opponents()) if voids else 0
        return (not mate_void, foes_void, -length[c.suit], c.suit.value, c.suit_rank_value())

    return min(suit_cards, key=key)


def _play(card: Card, key: str, **params) -> Decision:
    return Decision("play_card", {"card_id": card.id}, key, {"card": card.id, **params})


def _lead(view: SeatView) -> Decision:
    legal = view.legal_cards
    tarokks = sorted((c for c in legal if c.is_tarokk()), key=lambda c: c.tarokk_value())
    plain_tarokks = [c for c in tarokks if not _is(c, PAGAT)]
    out = tarokks_out(view)
    skiz_is_out = skiz_out(view)
    low_suit = _longest_suit_low(legal, view)
    trick_no = len(view.trick_history) + 1

    def strong_tarokks() -> List[Card]:
        """Tarokks worth leading: not the pagát, and not the XXI while the skíz can catch it."""
        return [c for c in plain_tarokks if not (_is(c, XXI) and skiz_is_out)]

    # I announced pagát ulti: draw the tarokks, keep the pagát for the end
    if _announced(view, "pagat_ultimo", by_me=True) and view.holds("I"):
        if out and strong_tarokks():
            pick = strong_tarokks()[0] if "ulti_small" in TACTICS else strong_tarokks()[-1]
            return _play(pick, "hint.lead.ulti_draw", count=len(out))
        if low_suit:
            return _play(low_suit, "hint.lead.ulti_keep_pagat")

    # Somebody on the other side announced pagát ulti: keep a tarokk for the last trick
    ulti_against = any(
        a.announcement_type.value == "pagat_ultimo" and not view.is_teammate(a.player_position)
        and a.player_position != view.position
        for a in view.announcements
    )
    if ulti_against and len(plain_tarokks) == 1 and low_suit:
        return _play(low_suit, "hint.lead.keep_tarokk_for_ulti", kept_card=plain_tarokks[0].id)

    # The owner's rule for defenders: protect the fellow defender's XXI
    if (not view.on_declarer_side and view.declarer_position is not None
            and not _announced(view, "trull") and not xxi_played(view) and not view.holds("XXI")):
        last_seat = (view.position + 3) % 4
        if view.is_teammate(last_seat) and plain_tarokks:
            return _play(plain_tarokks[0], "hint.lead.partner_last_tarokk")
        if low_suit:
            return _play(low_suit, "hint.lead.suit_protect_xxi")

    mates = view.teammates()
    # A teammate announced pagát ulti: help to draw the tarokks
    if ("ulti_support" in TACTICS and len(plain_tarokks) >= 2 and out and any(
            a.announcement_type.value == "pagat_ultimo" and a.player_position in mates
            for a in view.announcements)):
        return _play(plain_tarokks[0], "hint.lead.ulti_support")

    # Declarer's side with the upper hand in tarokks: draw them
    if view.on_declarer_side and out and len(tarokks) > len(out) / 2 and strong_tarokks():
        return _play(strong_tarokks()[-1], "hint.lead.draw_tarokks", count=len(out))

    if low_suit:
        return _play(low_suit, "hint.lead.long_suit")
    if plain_tarokks:
        return _play(plain_tarokks[0], "hint.lead.low_tarokk")
    return _play(legal[0], "hint.lead.only_card")


def _follow(view: SeatView) -> Decision:
    legal = view.legal_cards
    trick = view.current_trick
    if len(legal) == 1:
        return _play(legal[0], "hint.follow.only_card")

    seats_after = [(view.position + i) % 4 for i in range(1, 4 - len(trick))]
    foe_after = any(not view.is_teammate(seat) for seat in seats_after)
    winner_seat, winner_card = _winning_play(trick)
    out = tarokks_out(view)

    # Catch an opponent's XXI with the skíz
    skiz = next((c for c in legal if _is(c, SKIZ)), None)
    if skiz and any(_is(card, XXI) and not view.is_teammate(seat) for seat, card in trick):
        return _play(skiz, "hint.follow.catch_xxi")

    candidates = list(legal)
    # Do not walk the XXI into the skíz
    if skiz_out(view) and foe_after:
        safer = [c for c in candidates if not _is(c, XXI)]
        candidates = safer or candidates
    # An announced pagát ulti needs the pagát at the very end
    if _announced(view, "pagat_ultimo", by_me=True):
        kept = [c for c in candidates if not _is(c, PAGAT)]
        candidates = kept or candidates

    pagat = next((c for c in candidates if _is(c, PAGAT)), None)
    without_pagat = [c for c in candidates if not _is(c, PAGAT)] or candidates

    if view.is_teammate(winner_seat):
        # Is the teammate's card certain to hold?
        certain = not foe_after or (
            winner_card.is_tarokk() and all(value < winner_card.tarokk_value() for value in out)
        )
        if pagat and certain and not _announced(view, "pagat_ultimo", by_me=True):
            return _play(pagat, "hint.follow.pagat_home")
        suit_cards = [c for c in without_pagat if not c.is_tarokk()]
        if suit_cards and (certain or "safe_feed" not in TACTICS):
            return _play(max(suit_cards, key=lambda c: c.points), "hint.follow.feed_teammate")
        return _play(min(without_pagat, key=_cheapness), "hint.follow.teammate_wins_low")

    # Win it cheaply when it is worth something, or when nobody can answer
    winners = [c for c in candidates if _beats(c, trick)]
    if not seats_after:
        last_winners = winners
    else:
        last_winners = [c for c in winners if not _is(c, PAGAT)]
    trick_points = sum(card.points for _, card in trick)
    worth_it = trick_points >= 5 or ("stop_foe" in TACTICS and winner_seat in view.opponents())
    if last_winners and (not seats_after or worth_it):
        if not seats_after and pagat and pagat in last_winners:
            return _play(pagat, "hint.follow.pagat_home")
        cheapest = min(last_winners, key=lambda c: (c.tarokk_value(), c.suit_rank_value()))
        return _play(cheapest, "hint.follow.win_cheap")

    return _play(min(without_pagat, key=_cheapness), "hint.follow.low")


def decide_card(view: SeatView) -> Decision:
    if not view.current_trick:
        return _lead(view)
    return _follow(view)


# ----------------------------------------------------------------- dispatch

def decide(view: SeatView) -> Decision:
    if "signal_partner" in TACTICS and view.partner_position is None and not view.declarer_alone:
        # Four kings from a non-declarer tells the whole table who the partner is
        seat = _signal_seat(view)
        if seat is not None and seat != view.position:
            view.partner_position = seat
    if view.phase == GamePhase.BIDDING:
        return decide_bid(view)
    if view.phase == GamePhase.DISCARDING:
        return decide_discard(view)
    if view.phase == GamePhase.PARTNER_CALL:
        return decide_call(view)
    if view.phase == GamePhase.ANNOUNCEMENTS:
        return decide_announcement(view)
    if view.phase == GamePhase.PLAYING:
        return decide_card(view)
    raise ValueError(f"No action in phase {view.phase.value}")


def decide_for_seat(game_state: GameState, position: int) -> Decision:
    """What the seat should do now. Falls back to a plain legal move if a rule fails."""
    try:
        return decide(build_view(game_state, position))
    except Exception as e:
        logger.error("strategy_error", error=str(e), phase=game_state.phase.value, position=position)
        return fallback_decision(game_state, position)
