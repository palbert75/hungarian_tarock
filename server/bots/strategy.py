"""
Rule-based play for bots, and the same advice as tutorial hints.

Every function takes a SeatView (only what that seat may see) and returns a
Decision with a translatable reason. The rules come from the design document,
sections 5.2 (the owner's rules) and 5.3 (kept deliberately simple).
"""

from typing import List, Optional

import structlog

from bots.counting import PAGAT, SKIZ, XXI, observed_voids, played_cards, skiz_out, tarokks_out, xxi_played
from bots import route
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
    "declarer_tarokk", # the owner's rule: the declarer's side leads a tarokk whenever it has one
    "show_called",     # the owner's rule: the partner answers the declarer's tarokk lead with the called card
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
# Tarokks beside the XXI its holder needs before leading a small one to find the partner
XXI_FIND_PARTNER_TAROKKS = 3
# Tarokks above the XIII with which the enemy team says kontra to four kings
KONTRA_KINGS_HIGH = 5
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

    # The declarer's skart counts for the declarer's team, everybody else's against it. Whoever
    # expects to be called (holds the XX, or gave the invit the declarer took) discards cheap cards.
    my_invit_taken = bool(view.invit and view.invit["by"] == view.position)
    cheap_first = ("xx_cheap_skart" in TACTICS and view.position != view.declarer_position
                   and (view.holds("XX") or my_invit_taken))

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


def _partner_showed_tarokks(view: SeatView) -> bool:
    """
    My partner on the declarer's side announced four kings or declared eight or nine
    tarokks: either says "I hold a long tarokk hand". The declarer takes four kings
    from any other seat (the announcement itself shows the partner).
    """
    i_declare = view.position == view.declarer_position
    for a in view.announcements:
        if (a.announcement_type.value == "four_kings" and a.player_position != view.position
                and (i_declare or a.player_position == view.declarer_position)):
            return True
    partner = view.partner_position if i_declare else view.declarer_position
    return partner is not None and partner in view.tarokk_declarations


# What the declarer's side says first when it has more to say than fits into one turn
ANNOUNCE_PRIORITY = ["trull", "double_game", "nine_tarokks", "eight_tarokks", "four_kings", "pagat_ultimo"]
ANNOUNCE_PER_TURN = 2


def _one_turn_of(view: SeatView, wanted: list) -> list:
    """
    The owner's rule: announcements tell the partner about the hand, so the declarer's
    side says at most two things per turn and lets the partner answer. Trull always
    goes first. Four kings waits: for the next turn when double game is said now, and
    for the partner when I hold a pagát ulti hand (then I want to hear it from them)
    or when my tarokk count already says the same.
    """
    kinds = {w[0] for w in wanted}
    counted = view.position in view.tarokk_declarations or bool(kinds & {"eight_tarokks", "nine_tarokks"})
    ulti_chance = view.holds("I") and len(view.tarokks) >= ULTI_MIN_TAROKKS
    if "double_game" in kinds or counted or ulti_chance:
        wanted = [w for w in wanted if w[0] != "four_kings"]
    # A pagát ulti owed for an invit cannot wait: it is due at the first chance
    wanted = sorted(wanted, key=lambda w: -1 if w[1] == "hint.announce.ulti_obligatory"
                    else ANNOUNCE_PRIORITY.index(w[0]))
    return wanted[:ANNOUNCE_PER_TURN]


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
        # The owner's rule: trull says "our team holds both great honours". The partner
        # cannot see the declarer's hand, so it announces trull only when it holds both itself.
        if view.holds("skiz") and view.holds("XXI"):
            wanted.append(("trull", "hint.announce.trull_partner", {}))
    # At this table only the declarer's side announces: an announcement shows who is with whom
    my_side_declares = view.position == view.declarer_position or view.i_am_partner
    if (not any(w[0] == "trull" for w in wanted) and view.holds("skiz") and view.holds("XXI")
            and view.position == view.declarer_position):
        # The owner's rule: the declarer holding both great honours announces trull
        wanted.append(("trull", "hint.announce.trull_two", {}))
    top = len([c for c in view.tarokks if c.tarokk_value() >= 17])
    # The owner's rule: with only eight tarokks, wait until the partner has shown a long tarokk hand
    eight_allowed = _partner_showed_tarokks(view)
    ulti_hand = tarokk_count >= ULTI_SURE_TAROKKS or (
        tarokk_count >= ULTI_MIN_TAROKKS and top >= ULTI_MIN_HIGH and eight_allowed)
    if my_side_declares and view.holds("I") and ulti_hand and not view.must_ulti:
        wanted.append(("pagat_ultimo", "hint.announce.pagat_ultimo", {"count": tarokk_count}))

    if ("signal_double" in TACTICS and view.position == view.declarer_position and tarokk_count >= 6
            and (view.holds("skiz") or view.holds("XXI")) and _signal_seat(view) is not None):
        wanted.append(("double_game", "hint.announce.double_after_signal", {"count": tarokk_count}))

    # Eight or nine tarokks: every other player pays for it, so it is always declared
    declaration = next((k for k in ("nine_tarokks", "eight_tarokks") if k in valid), None)
    # The owner's rule: the declarer's side shows its tarokk count only once trull is called
    trull_called = _announced(view, "trull") or any(w[0] == "trull" for w in wanted)
    if declaration and (not my_side_declares or trull_called):
        wanted.append((declaration, "hint.announce.tarokks", {"count": tarokk_count}))

    wanted = [w for w in wanted if w[0] in valid]
    if my_side_declares:
        wanted = _one_turn_of(view, wanted)
    if not wanted and "kontra" in TACTICS:
        foes = view.opponents()
        for a in view.announcements:
            if a.contra or a.player_position not in foes:
                continue
            kind = a.announcement_type.value
            if kind == "four_kings" and not my_side_declares and high >= KONTRA_KINGS_HIGH:
                # The owner's rule: the enemy team says kontra with five tarokks above the XIII
                return Decision("contra", {"announcement_type": kind}, "hint.announce.kontra_four_kings_high",
                                {"count": high})
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


def _xxi_at_risk(view: SeatView) -> bool:
    """I hold the XXI and the skíz may still catch it: it is in another hand, and not a teammate's."""
    if not view.holds("XXI") or not skiz_out(view):
        return False
    # Trull on my side means we hold both great honours: the skíz is my teammate's
    return not _side_announced(view, {"trull"})


def _pagat_must_go(view: SeatView, still_to_play: int) -> Optional[Card]:
    """
    The owner's rule: count the tarokks. In the second-last trick, with the pagát and one more
    card in hand: if more tarokks are out than players still to play to this trick, one of them
    is left for the last trick and beats the pagát there, which is a lost silent pagát ulti
    whoever takes it. Then the pagát goes now. An announced ulti is lost either way.
    """
    if len(view.hand) != 2 or _announced(view, "pagat_ultimo", by_me=True):
        return None
    if len(view.legal_cards) != 2 or len(tarokks_out(view)) <= still_to_play:
        return None
    return next((c for c in view.legal_cards if _is(c, PAGAT)), None)


def _shortest_suit_low(cards: List[Card], view: SeatView) -> Optional[Card]:
    """The lowest card of the suit I hold fewest cards of: soon I can trump it."""
    suit_cards = [c for c in cards if not c.is_tarokk()]
    if not suit_cards:
        return None
    length = {s: len([c for c in view.hand if c.suit == s]) for s in Suit}
    return min(suit_cards, key=lambda c: (length[c.suit], c.points, c.suit.value))


def _readable_suit_lead(view: SeatView, pick: Optional[Card]) -> Optional[Card]:
    """
    The owner's convention for the caller's team: a suit lead comes from a suit whose king I do
    not hold; with a king in every suit I have, I lead the king itself. So my partner can tell
    where the king is.
    """
    if pick is None or not view.on_declarer_side or pick.is_king():
        return pick
    kings = {c.suit for c in view.hand if c.is_king()}
    if pick.suit not in kings:
        return pick
    length = {s: len([c for c in view.hand if c.suit == s]) for s in Suit}
    kingless = [c for c in view.legal_cards if not c.is_tarokk() and c.suit not in kings]
    if kingless:
        return min(kingless, key=lambda c: (length[c.suit], c.points, c.suit.value))
    return next(c for c in view.legal_cards if c.is_king() and c.suit == pick.suit)


def _king_holder(view: SeatView) -> Optional[int]:
    """
    The seat that must hold the king of the suit led, and so has to follow suit.
    My teammate on the caller's team led a low card of the suit, so by our convention the king
    is not theirs; it is not mine, a king cannot lie in the skart, and all but one of the
    other players have shown they are out of the suit.
    """
    lead_seat, lead_card = view.current_trick[0]
    if lead_card.is_tarokk() or lead_card.is_king():
        return None
    if not view.on_declarer_side or not view.is_teammate(lead_seat):
        return None
    if any(c.is_king() and c.suit == lead_card.suit for c in view.hand + played_cards(view)):
        return None
    voids = observed_voids(view)
    seats = [s for s in range(4) if s not in (view.position, lead_seat) and (s, lead_card.suit) not in voids]
    return seats[0] if len(seats) == 1 else None


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

    doomed_pagat = _pagat_must_go(view, 3)
    if doomed_pagat:
        return _play(doomed_pagat, "hint.lead.pagat_drop", count=len(out))

    # The owner's rules for the XXI while the skíz can still catch it. Leading it is never safe.
    if _xxi_at_risk(view):
        others = [c for c in plain_tarokks if not _is(c, XXI)]
        if view.on_declarer_side:
            if not view.teammates():
                # Partner not shown yet: a small tarokk lets them answer with the called card
                if others and len(view.tarokks) - 1 >= XXI_FIND_PARTNER_TAROKKS:
                    return _play(others[0], "hint.lead.xxi_find_partner")
            elif others and len(others) > (len(out) - 1) / 2:
                # Enough tarokks to run the skíz's hand dry: lead high ones until the skíz must fall
                return _play(others[-1], "hint.lead.xxi_drive_skiz")
            short = _readable_suit_lead(view, _shortest_suit_low(legal, view))
            if short:
                return _play(short, "hint.lead.xxi_short_suit")
        elif low_suit:
            return _play(low_suit, "hint.lead.xxi_suit")

    # I hold the skíz and the XXI is still out: a tarokk lead lets the XXI slip home
    # under it, so lead a suit and wait
    if _hunting(view):
        # The owner's rule: so few tarokks are left that the three others cannot keep the XXI back
        skiz_card = next((c for c in legal if _is(c, SKIZ)), None)
        if skiz_card and len(out) <= 3:
            return _play(skiz_card, "hint.lead.skiz_force", count=len(out))
        suit = _kingless_suit_low(legal, view)
        if suit:
            return _play(suit, "hint.lead.skiz_suit")
        small = [c for c in plain_tarokks if not _is(c, SKIZ)]
        if small:
            return _play(small[0], "hint.lead.skiz_low_tarokk")

    # The owner's rule: once trull is called, the enemy team leads suits. (The caller's team
    # leads tarokks; the rules further down pick which one.)
    # Four kings or double game announced: the enemy team's suit leads avoid the suits of its own kings
    kings_bid = _announced(view, "four_kings") or _announced(view, "double_game")
    enemy_suit = (_kingless_suit_low(legal, view) if kings_bid else None) or low_suit
    if _announced(view, "trull") and view.declarer_position is not None and not view.on_declarer_side and low_suit:
        return _play(enemy_suit, "hint.lead.trull_suit")

    # A teammate behind me waits with the skíz: drive the XXI out with high tarokks
    waiting_seat = _waiting_skiz_seat(view) if "skiz_drive" in TACTICS else None
    if waiting_seat == (view.position + 3) % 4 and strong_tarokks():
        return _play(strong_tarokks()[-1], "hint.lead.drive_for_skiz")

    # Trull is announced on my side and the pagát has not shown: draw tarokks until it falls
    if ("pagat_catch" in TACTICS and _side_announced(view, {"trull"}) and PAGAT in out
            and len(plain_tarokks) >= 5 and strong_tarokks()):
        return _play(strong_tarokks()[-1], "hint.lead.catch_pagat")

    defender = not view.on_declarer_side and view.declarer_position is not None
    # The owner's rule for defenders: protect the fellow defender's XXI
    # Only for a hand with neither great honour: the skíz wants to catch the XXI, not protect it
    protecting = (defender and not _announced(view, "trull") and not xxi_played(view) and not view.holds("XXI")
                  and not view.holds("skiz") and not _skiz_played(view))
    if protecting and view.is_teammate((view.position + 3) % 4) and plain_tarokks:
        return _play(plain_tarokks[0], "hint.lead.partner_last_tarokk")

    # The owner's rule: four kings or double game is announced. The enemy team leads a suit whose
    # king it does not hold. (The caller's team leads tarokks; the rules further down pick which one.)
    if kings_bid and defender and enemy_suit:
        return _play(enemy_suit, "hint.lead.kings_suit")

    # Skíz or XXI already gone: nothing left to protect, a defender leads a suit
    if defender and (xxi_played(view) or _skiz_played(view)) and low_suit:
        return _play(low_suit, "hint.lead.defender_suit")

    if protecting and low_suit:
        return _play(low_suit, "hint.lead.suit_protect_xxi")

    # The owner's rule: catching or saving the XXI comes before any pagát ulti business
    # I announced pagát ulti: draw the tarokks, keep the pagát for the end
    if _announced(view, "pagat_ultimo", by_me=True) and view.holds("I"):
        if out and strong_tarokks():
            pick = strong_tarokks()[0] if "ulti_small" in TACTICS else strong_tarokks()[-1]
            return _play(pick, "hint.lead.ulti_draw", count=len(out))
        if low_suit:
            # The owner's rule: any suit, but a king if I hold one. It should keep the lead,
            # and a tarokk led by somebody else would pull the pagát out too early.
            kings = [c for c in legal if c.is_king()]
            return _play(min(kings, key=lambda c: c.suit.value) if kings else low_suit, "hint.lead.ulti_keep_pagat")

    # Somebody on the other side announced pagát ulti: keep a tarokk for the last trick
    ulti_against = any(
        a.announcement_type.value == "pagat_ultimo" and not view.is_teammate(a.player_position)
        and a.player_position != view.position
        for a in view.announcements
    )
    if ulti_against and len(plain_tarokks) == 1 and low_suit:
        return _play(low_suit, "hint.lead.keep_tarokk_for_ulti", kept_card=plain_tarokks[0].id)

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

    # The owner's rule: the declarer's side leads a tarokk whenever it has one. The XXI-catch
    # cases come first: the skíz waiting for the XXI (above), and the XXI kept back from the skíz.
    if "declarer_tarokk" in TACTICS and view.on_declarer_side and strong_tarokks():
        return _play(strong_tarokks()[0], "hint.lead.declarer_tarokk")

    if low_suit:
        return _play(_readable_suit_lead(view, low_suit), "hint.lead.long_suit")
    if plain_tarokks:
        return _play(plain_tarokks[0], "hint.lead.low_tarokk")
    return _play(legal[0], "hint.lead.only_card")


def _follow(view: SeatView) -> Decision:
    legal = view.legal_cards
    trick = view.current_trick
    if len(legal) == 1:
        return _play(legal[0], "hint.follow.only_card")

    seats_after = [(view.position + i) % 4 for i in range(1, 4 - len(trick))]
    winner_seat, winner_card = _winning_play(trick)
    out = tarokks_out(view)
    # The owner's rule: a player who must hold the king of the suit led has to follow suit,
    # and cannot beat a tarokk. Once the trick is trumped, they are no danger after me.
    bound = _king_holder(view)
    if bound not in seats_after or not (winner_card.is_tarokk() or all(c.is_tarokk() for c in legal)):
        bound = None
    foe_after = any(not view.is_teammate(seat) and seat != bound for seat in seats_after)

    # The owner's rule: nobody who could hold the skíz plays after me, so the XXI escapes now
    at_risk = _xxi_at_risk(view)
    xxi = next((c for c in legal if _is(c, XXI)), None)
    if at_risk and xxi and bound is not None and not foe_after:
        return _play(xxi, "hint.follow.xxi_escape_king")
    if at_risk and xxi and not foe_after:
        return _play(xxi, "hint.follow.xxi_escape")

    # Catch an opponent's XXI with the skíz
    skiz = next((c for c in legal if _is(c, SKIZ)), None)
    if skiz and any(_is(card, XXI) and not view.is_teammate(seat) for seat, card in trick):
        return _play(skiz, "hint.follow.catch_xxi")

    doomed_pagat = _pagat_must_go(view, len(seats_after))
    if doomed_pagat:
        return _play(doomed_pagat, "hint.follow.pagat_drop", count=len(out))

    # The declarer leads a tarokk: the called partner answers with the called card, so the
    # table sees who is with whom and the opponents do not get the lead for a small tarokk
    lead_seat, lead_card = trick[0]
    called = next((c for c in legal if c.is_tarokk() and view.called_rank
                   and c.rank.upper() == view.called_rank.upper()), None)
    # The owner's rule: not with a great honour, whose holder has the XXI catch to think of first
    if ("show_called" in TACTICS and called and view.i_am_partner and foe_after
            and not view.holds("skiz") and not view.holds("XXI")
            and lead_seat == view.declarer_position and lead_card.is_tarokk() and _beats(called, trick)):
        return _play(called, "hint.follow.show_called")

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

    # The owner's rule: the XXI cannot go yet. Stay out of the lead (leading never frees it);
    # if the player after me takes the trick, I play last to the next one.
    if at_risk and foe_after:
        losers = [c for c in without_pagat if not _is(c, XXI) and not _beats(c, trick)]
        if losers:
            return _play(min(losers, key=_cheapness), "hint.follow.xxi_duck")

    # Waiting with the skíz for the XXI: stay out of the lead, and shed high tarokks doing so
    if _hunting(view):
        # The owner's rule: a tarokk was led and no more tarokks are out than players still to
        # play, so the XXI has to come: play the skíz before it shows
        if skiz and lead_card.is_tarokk() and seats_after and len(out) <= len(seats_after):
            return _play(skiz, "hint.follow.skiz_force", count=len(out))
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

    # The owner's rule: once trull is called, every trick counts. Win it whenever I can, unless my
    # team already holds it for certain; with an opponent still to play, win it with my best card.
    if _announced(view, "trull"):
        team_safe = view.is_teammate(winner_seat) and (not foe_after or (
            winner_card.is_tarokk() and all(value < winner_card.tarokk_value() for value in out)))
        can_win = [c for c in candidates if _beats(c, trick) and (not seats_after or not _is(c, PAGAT))]
        if can_win and not team_safe:
            if foe_after:
                best = _hard_tarokk(can_win, out, trick_points) or max(can_win, key=lambda c: c.suit_rank_value())
            elif pagat in can_win:
                best = pagat
            else:
                best = min(can_win, key=lambda c: (c.tarokk_value(), c.suit_rank_value()))
            return _play(best, "hint.follow.trull_win")

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


def tree_of(view: SeatView) -> str:
    """Which tree of the decision tree page this decision is taken in."""
    if view.phase == GamePhase.BIDDING:
        return "A"
    if view.phase == GamePhase.DISCARDING:
        return "D"
    if view.phase == GamePhase.PARTNER_CALL:
        return "B1"
    if view.phase == GamePhase.ANNOUNCEMENTS:
        if view.position == view.declarer_position:
            return "B.declarer"
        return "B.partner" if view.i_am_partner else "B.enemy"
    # Card play: branch I while the XXI can still be caught, branch II once that is settled
    settled = (_announced(view, "trull") or xxi_played(view) or _skiz_played(view)
               or (view.holds("skiz") and view.holds("XXI")))
    return "C.II" if settled else "C.I"


def decide_for_seat(game_state: GameState, position: int) -> Decision:
    """What the seat should do now. Falls back to a plain legal move if a rule fails."""
    try:
        view = build_view(game_state, position)
        tree = tree_of(view)
        decision, decision.route = route.record(decide, view)
        decision.boxes = route.name_boxes(decision.route, tree)
        return decision
    except Exception as e:
        logger.error("strategy_error", error=str(e), phase=game_state.phase.value, position=position)
        return fallback_decision(game_state, position)


# The functions whose checks make up the decision trees
route.watch(decide_bid, _decide_bid, decide_discard, decide_call, decide_announcement, _one_turn_of,
            decide_card, _lead, _follow)
