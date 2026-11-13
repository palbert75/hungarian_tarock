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
# "signal_double" (the declarer answers the four-kings signal with double game) won
# while a lost double game cost nothing; now that it costs four times the game it
# loses about a quarter point per hand, so it is off.
# "invit_give" (jump bid with the XIX, a great honour and six tarokks) is off too: such
# a hand wins more by bidding normally (-0.18 per hand; -0.13 with seven tarokks, -0.03
# with eight). Bots follow an invit somebody else gives; they do not start one.
ADOPTED = frozenset({
    "voids",           # lead suits a teammate cannot follow, avoid those an opponent cannot
    "stop_foe",        # take a trick a known opponent is winning
    "safe_feed",       # give points only to a trick that is certain
    "ulti_small",      # pagát ulti announcer draws tarokks with small ones
    "ulti_support",    # the announcer's teammate leads tarokks too
    "signal_partner",  # an announcement from a non-declarer shows the table who the partner is
    "partner_double",  # the owner's rule: the partner announces double game with five tarokks above the XIII
    "xx_cheap_skart",  # a non-declarer holding the XX discards cheap cards
    "skiz_hunt",       # the skíz waits for the other side's XXI: leads suits, ducks tricks
    "hit_hard",        # trump high when an opponent still plays after me and a king is at stake
    "hit_hard_lead",   # the same on a teammate's suit lead, to keep the lead on our side
    "bid_over_three",  # with the pagát, say "two" over a "three" from the seat before me
    "skiz_weak_skart", # the skíz without the XXI discards high tarokks to stay out of the lead
    "skiz_drive",      # win tricks and lead high tarokks when the skíz behind me waits for the XXI
    "kurta",           # the long hand leaves cheap early tricks to the shorter teammate
    "pagat_catch",     # with trull announced on my side, draw tarokks until the pagát falls
    "ulti_keep_small", # the ulti announcer's teammate keeps a small tarokk for last
    "kontra",          # kontra four kings and pagát ulti with a long, high tarokk hand
    "invit_accept",    # a great honour takes the auction after somebody's invit
    "invit_trull",     # the owner's rule: whoever takes an invit with a great honour announces trull
    "yield_game",      # pass a "three" to a lone "two" with the XX and a great honour
})
TACTICS: set = set(ADOPTED)

# Pagát ulti: nine tarokks, or eight when three of them are XVII or higher
ULTI_SURE_TAROKKS = 9
ULTI_MIN_TAROKKS = 8
ULTI_MIN_HIGH = 3
# Tarokks a skíz keeps when it discards to wait for the XXI
SKIZ_HUNT_TAROKKS = 6
# Kontra: tarokks needed against four kings (with two at XVII or above) and against pagát ulti
KONTRA_KINGS_TAROKKS = 6
KONTRA_ULTI_TAROKKS = 7
# Tarokks needed (with all three honours) before a bot announces trull
TRULL_MIN_TAROKKS = 7
# Tarokks needed (with the invited card and a great honour) to give an invit
INVIT_MIN_TAROKKS = 6
# Tarokks needed to accept an invit at solo level
INVIT_SOLO_TAROKKS = 6


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
    decision = _decide_bid(view)
    if decision.payload["bid_type"] == "pass" and "pass" not in view.valid_bids:
        # Passing here would be a yielded game, which needs the XX and a great honour
        bid = _next_bid(view)
        if bid is not None:
            return Decision("bid", {"bid_type": bid}, "hint.bid.must_hold", {"bid": bid})
    return decision


def _decide_bid(view: SeatView) -> Decision:
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
    big = has_skiz or has_xxi

    invit = view.invit
    if invit and invit["by"] == view.position:
        if view.highest_bidder != view.position:
            # Somebody took my invit: they will call my card
            return pass_("hint.bid.invit_taken", card=invit["card"])
    elif invit and "invit_accept" in TACTICS and big:
        # The inviter holds that card and a strong hand: become declarer and call it
        if level < BID_LEVEL["solo"] or tarokk_count >= INVIT_SOLO_TAROKKS:
            return Decision("bid", {"bid_type": bid}, "hint.bid.invit_accept", {"bid": bid, "card": invit["card"]})
    if "invit_give" in TACTICS and big and tarokk_count >= INVIT_MIN_TAROKKS:
        jumps = [b for b, card in view.invit_bids.items() if card == "XIX" and BID_LEVEL[b] <= BID_LEVEL["one"]]
        if jumps:
            return Decision("bid", {"bid_type": jumps[0]}, "hint.bid.invit_give", {"bid": jumps[0], "card": "XIX"})
    if "yield_game" in TACTICS and view.yield_turn and "pass" in view.valid_bids:
        # The pass itself says: I hold the XX and a great honour, call me
        return pass_("hint.bid.yield")

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
    if "bid_over_three" in TACTICS and bid == "two" and view.highest_bid == "three":
        real = [b for b in view.bid_history if b.bid_type.value in BID_LEVEL]
        mine = any(b.player_position == view.position for b in real)
        if real and not mine and real[-1].player_position == (view.position + 3) % 4:
            # Left alone at "two" this is a yielded game with a strong partner; if the
            # other goes on, I have at least taken more cards from the talon
            return Decision("bid", {"bid_type": bid}, "hint.bid.two_over_three", {"bid": bid})
    if tarokk_count < 8:
        return pass_("hint.bid.pagat_few_tarokks", count=tarokk_count)
    if level > BID_LEVEL["two"]:
        return pass_("hint.bid.limit_reached", bid=view.highest_bid)
    return Decision("bid", {"bid_type": bid}, "hint.bid.pagat_many_tarokks", {"bid": bid, "count": tarokk_count})


# -------------------------------------------------------------------- skart

def decide_discard(view: SeatView) -> Decision:
    count = view.discard_count
    allowed = [c for c in view.hand if c.can_be_discarded()]
    if view.invit and view.invit["by"] == view.position:
        # The card I invited with stays in my hand
        allowed = [c for c in allowed if not (c.is_tarokk() and c.rank == view.invit["card"])]
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
    key = None
    # The skíz hoping to catch the XXI wants to stay out of the lead: five or six
    # small tarokks beside it are ideal, so the high ones go first
    if ("skiz_weak_skart" in TACTICS and view.holds("skiz") and not view.holds("XXI")
            and len(view.tarokks) > SKIZ_HUNT_TAROKKS):
        spare = len(view.tarokks) - SKIZ_HUNT_TAROKKS
        shed = list(reversed(tarokks))[:min(spare, count)]
        if shed:
            ordered = shed + [c for c in ordered if c not in shed]
            key = "hint.discard.skiz_weaken"
    chosen = ordered[:count]
    if key is None:
        key = "hint.discard.with_tarokks" if any(c.is_tarokk() for c in chosen) else "hint.discard.suits"
    return Decision("discard", {"card_ids": [c.id for c in chosen]}, key, {"cards": [c.id for c in chosen]})


# ------------------------------------------------------------- partner call

def decide_call(view: SeatView) -> Decision:
    if view.required_call:
        rank = view.required_call
        key = "hint.call.invit" if view.invit and view.invit["by"] != view.position else "hint.call.yielded"
        return Decision("call_partner", {"tarokk_rank": rank}, key, {"rank": rank})
    held = {c.rank for c in view.tarokks}
    rank = next((r for r in CALL_ORDER if r not in held), CALL_ORDER[0])
    key = "hint.call.xx" if rank == CALL_ORDER[0] else "hint.call.lower"
    return Decision("call_partner", {"tarokk_rank": rank}, key, {"rank": rank})


# ------------------------------------------------------------ announcements

def _signal_seat(view: SeatView) -> Optional[int]:
    """
    The seat other than the declarer that announced something: by the table's
    convention the caller's partner (defenders only answer with kontra).
    """
    for a in view.announcements:
        if a.announced and a.player_position != view.declarer_position:
            return a.player_position
    return None


def decide_announcement(view: SeatView) -> Decision:
    valid = set(view.valid_announcements)
    tarokk_count = len(view.tarokks)
    high = len([c for c in view.tarokks if c.tarokk_value() > 13])
    wanted = []  # (type, reason key, params)

    if view.must_ulti:
        wanted.append(("pagat_ultimo", "hint.announce.ulti_obligatory", {}))
    accepted_invit = (view.invit is not None and view.position == view.declarer_position
                      and view.invit["by"] != view.position and view.called_rank == view.invit["card"])
    if "invit_trull" in TACTICS and accepted_invit and (view.holds("skiz") or view.holds("XXI")):
        # Whoever takes an invit with a great honour announces trull
        wanted.append(("trull", "hint.announce.trull_invit", {"card": view.invit["card"]}))

    if view.i_am_partner:
        if tarokk_count >= 6:
            wanted.append(("four_kings", "hint.announce.four_kings", {"count": tarokk_count}))
        if "partner_double" in TACTICS and high >= 5:
            wanted.append(("double_game", "hint.announce.double_game", {"count": high}))
        # The called partner holding a great honour announces trull
        if view.holds("skiz") or view.holds("XXI"):
            wanted.append(("trull", "hint.announce.trull_partner", {}))
    # At this table only the declarer's side announces: an announcement shows who is with whom
    my_side_declares = view.position == view.declarer_position or view.i_am_partner
    if (my_side_declares and not any(w[0] == "trull" for w in wanted) and view.holds("skiz") and view.holds("XXI")
            and view.holds("I") and tarokk_count >= TRULL_MIN_TAROKKS):
        wanted.append(("trull", "hint.announce.trull", {}))
    if (not any(w[0] == "trull" for w in wanted) and view.holds("skiz") and view.holds("XXI")
            and view.position == view.declarer_position):
        # The owner's rule: the declarer holding both great honours announces trull
        wanted.append(("trull", "hint.announce.trull_two", {}))
    top = len([c for c in view.tarokks if c.tarokk_value() >= 17])
    ulti_hand = tarokk_count >= ULTI_SURE_TAROKKS or (tarokk_count >= ULTI_MIN_TAROKKS and top >= ULTI_MIN_HIGH)
    if my_side_declares and view.holds("I") and ulti_hand and not view.must_ulti:
        wanted.append(("pagat_ultimo", "hint.announce.pagat_ultimo", {"count": tarokk_count}))

    if ("signal_double" in TACTICS and view.position == view.declarer_position and tarokk_count >= 6
            and (view.holds("skiz") or view.holds("XXI")) and _signal_seat(view) is not None):
        wanted.append(("double_game", "hint.announce.double_after_signal", {"count": tarokk_count}))

    # Eight or nine tarokks: every other player pays for it, so it is always declared
    declaration = next((k for k in ("nine_tarokks", "eight_tarokks") if k in valid), None)
    if declaration:
        wanted.append((declaration, "hint.announce.tarokks", {"count": tarokk_count}))

    wanted = [w for w in wanted if w[0] in valid]
    if not wanted and "kontra" in TACTICS:
        foes = view.opponents()
        for a in view.announcements:
            if a.contra or a.player_position not in foes:
                continue
            kind = a.announcement_type.value
            if kind == "four_kings" and tarokk_count >= KONTRA_KINGS_TAROKKS and top >= 2:
                return Decision("contra", {"announcement_type": kind}, "hint.announce.kontra_four_kings",
                                {"count": tarokk_count})
            if kind == "pagat_ultimo" and tarokk_count >= KONTRA_ULTI_TAROKKS:
                return Decision("contra", {"announcement_type": kind}, "hint.announce.kontra_ulti",
                                {"count": tarokk_count})
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


def _skiz_played(view: SeatView) -> bool:
    return not view.holds("skiz") and not skiz_out(view)


def _hunting(view: SeatView) -> bool:
    """I hold the skíz and the XXI may still be caught: it is out, and nothing says my side holds it."""
    if "skiz_hunt" not in TACTICS or not view.holds("skiz") or view.holds("XXI") or xxi_played(view):
        return False
    # Trull announced on my side means we hold both great honours
    return not any(
        a.announcement_type.value == "trull"
        and (a.player_position == view.position or view.is_teammate(a.player_position))
        for a in view.announcements
    )


def _side_announced(view: SeatView, kinds) -> bool:
    return any(
        a.announcement_type.value in kinds
        and (a.player_position == view.position or view.is_teammate(a.player_position))
        for a in view.announcements
    )


def _mate_announced(view: SeatView, kinds) -> bool:
    return any(
        a.announcement_type.value in kinds and view.is_teammate(a.player_position)
        for a in view.announcements
    )


def _waiting_skiz_seat(view: SeatView) -> Optional[int]:
    """
    A teammate who seems to wait with the skíz for the XXI: the skíz is still out
    and they threw a high tarokk (XIV or above) under a higher card instead of winning.
    """
    if view.holds("skiz") or not skiz_out(view) or xxi_played(view) or view.holds("XXI"):
        return None
    for trick in view.trick_history:
        best = _winning_play(trick)
        for seat, card in trick:
            if (seat != best[0] and view.is_teammate(seat) and card.is_tarokk()
                    and 14 <= card.tarokk_value() < XXI):
                return seat
    return None


def _keep_smallest(view: SeatView, pick: Card, cards: List[Card]) -> Card:
    """The ulti announcer's teammate holds on to the smallest tarokk: play the next one up."""
    if "ulti_keep_small" not in TACTICS or not pick.is_tarokk() or not _mate_announced(view, {"pagat_ultimo"}):
        return pick
    mine = sorted((c for c in view.hand if c.is_tarokk() and not _is(c, PAGAT)), key=lambda c: c.tarokk_value())
    if len(mine) < 2 or pick.id != mine[0].id:
        return pick
    others = sorted((c for c in cards if c.is_tarokk() and c.id != pick.id and not _is(c, PAGAT)
                     and not _is(c, SKIZ) and not _is(c, XXI)), key=lambda c: c.tarokk_value())
    return others[0] if others else pick


def _kingless_suit_low(cards: List[Card], view: SeatView) -> Optional[Card]:
    """Lowest card of a suit whose king I do not hold; the XXI's holder is likelier to have to follow it."""
    suit_cards = [c for c in cards if not c.is_tarokk()]
    kingless = [c for c in suit_cards if not any(h.is_king() and h.suit == c.suit for h in view.hand)]
    pool = kingless or suit_cards
    return min(pool, key=lambda c: (c.points, c.suit.value)) if pool else None


def _hard_tarokk(cards: List[Card], out: List[int], trick_points: int) -> Optional[Card]:
    """
    A tarokk that should hold the trick: the lowest one nobody can beat, else my highest.
    The skíz is spent this way only on a trick worth a king.
    """
    tarokks = [c for c in cards if c.is_tarokk() and not _is(c, PAGAT)]
    if trick_points < 5:
        tarokks = [c for c in tarokks if not _is(c, SKIZ)] or tarokks
    if not tarokks:
        return None
    certain = [c for c in tarokks if all(value < c.tarokk_value() for value in out)]
    if certain:
        return min(certain, key=lambda c: c.tarokk_value())
    return max(tarokks, key=lambda c: c.tarokk_value())


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

    # I hold the skíz and the XXI is still out: a tarokk lead lets the XXI slip home
    # under it, so lead a suit and wait
    if _hunting(view):
        suit = _kingless_suit_low(legal, view)
        if suit:
            return _play(suit, "hint.lead.skiz_suit")
        small = [c for c in plain_tarokks if not _is(c, SKIZ)]
        if small:
            return _play(small[0], "hint.lead.skiz_low_tarokk")

    # A teammate behind me waits with the skíz: drive the XXI out with high tarokks
    waiting_seat = _waiting_skiz_seat(view) if "skiz_drive" in TACTICS else None
    if waiting_seat == (view.position + 3) % 4 and strong_tarokks():
        return _play(strong_tarokks()[-1], "hint.lead.drive_for_skiz")

    # Trull is announced on my side and the pagát has not shown: draw tarokks until it falls
    if ("pagat_catch" in TACTICS and _side_announced(view, {"trull"}) and PAGAT in out
            and len(plain_tarokks) >= 5 and strong_tarokks()):
        return _play(strong_tarokks()[-1], "hint.lead.catch_pagat")

    defender = not view.on_declarer_side and view.declarer_position is not None
    # Skíz or XXI already gone: nothing left to protect, a defender leads a suit
    if defender and (xxi_played(view) or _skiz_played(view)) and low_suit:
        return _play(low_suit, "hint.lead.defender_suit")

    # The owner's rule for defenders: protect the fellow defender's XXI
    # Only for a hand with neither great honour: the skíz wants to catch the XXI, not protect it
    if (defender and not _announced(view, "trull") and not xxi_played(view) and not view.holds("XXI")
            and not view.holds("skiz") and not _skiz_played(view)):
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
        pick = plain_tarokks[1] if "ulti_keep_small" in TACTICS else plain_tarokks[0]
        return _play(pick, "hint.lead.ulti_support")

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
    trick_points = sum(card.points for _, card in trick)
    lead_seat, lead_card = trick[0]
    king_at_stake = any(card.is_king() for _, card in trick)

    # Waiting with the skíz for the XXI: stay out of the lead, and shed high tarokks doing so
    if _hunting(view):
        waiting = [c for c in without_pagat if not _is(c, SKIZ)]
        losers = [c for c in waiting if not _beats(c, trick)]
        if losers:
            if all(c.is_tarokk() for c in losers):
                return _play(max(losers, key=lambda c: c.tarokk_value()), "hint.follow.skiz_duck_high")
            if view.is_teammate(winner_seat):
                return _play(max(losers, key=lambda c: c.points), "hint.follow.feed_teammate")
            return _play(min(losers, key=_cheapness), "hint.follow.skiz_duck")
        if waiting:
            return _play(min(waiting, key=_cheapness), "hint.follow.skiz_forced")

    # An opponent still plays after me: do not save tarokks when a king is at stake
    # or when my teammate led a suit I cannot follow
    hit_hard = (
        "hit_hard" in TACTICS and foe_after and all(c.is_tarokk() for c in without_pagat)
        and (king_at_stake or ("hit_hard_lead" in TACTICS and view.is_teammate(lead_seat)
                               and not lead_card.is_tarokk()))
    )

    if view.is_teammate(winner_seat):
        # Is the teammate's card certain to hold?
        certain = not foe_after or (
            winner_card.is_tarokk() and all(value < winner_card.tarokk_value() for value in out)
        )
        if pagat and certain and not _announced(view, "pagat_ultimo", by_me=True):
            return _play(pagat, "hint.follow.pagat_home")
        if hit_hard and not certain and not winner_card.is_tarokk():
            hard = _hard_tarokk(without_pagat, out, trick_points)
            if hard:
                return _play(hard, "hint.follow.hit_hard")
        suit_cards = [c for c in without_pagat if not c.is_tarokk()]
        if suit_cards and (certain or "safe_feed" not in TACTICS):
            return _play(max(suit_cards, key=lambda c: c.points), "hint.follow.feed_teammate")
        low = _keep_smallest(view, min(without_pagat, key=_cheapness), without_pagat)
        return _play(low, "hint.follow.teammate_wins_low")

    # Win it cheaply when it is worth something, or when nobody can answer
    winners = [c for c in candidates if _beats(c, trick)]
    if not seats_after:
        last_winners = winners
    else:
        last_winners = [c for c in winners if not _is(c, PAGAT)]
    if hit_hard and last_winners:
        hard = _hard_tarokk(last_winners, out, trick_points)
        if hard:
            return _play(hard, "hint.follow.hit_hard")
    worth_it = trick_points >= 5 or ("stop_foe" in TACTICS and winner_seat in view.opponents())
    reason = "hint.follow.win_cheap"
    # "Kurta üt": I am the long hand and a teammate still plays after me. Early on,
    # leave a cheap trick to the shorter hand and keep my masters for the end.
    if ("kurta" in TACTICS and last_winners and trick_points < 5 and len(view.trick_history) < 4
            and len(view.tarokks) >= 7 and any(view.is_teammate(seat) for seat in seats_after)):
        return _play(_keep_smallest(view, min(without_pagat, key=_cheapness), without_pagat),
                     "hint.follow.leave_to_short_hand")
    if last_winners and seats_after and not worth_it:
        # A teammate waits with the skíz behind me: get the lead to drive the XXI out
        if "skiz_drive" in TACTICS and _waiting_skiz_seat(view) == (view.position + 3) % 4:
            worth_it, reason = True, "hint.follow.win_to_drive"
    if last_winners and (not seats_after or worth_it):
        if not seats_after and pagat and pagat in last_winners:
            return _play(pagat, "hint.follow.pagat_home")
        cheapest = min(last_winners, key=lambda c: (c.tarokk_value(), c.suit_rank_value()))
        return _play(cheapest, reason)

    return _play(_keep_smallest(view, min(without_pagat, key=_cheapness), without_pagat), "hint.follow.low")


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
