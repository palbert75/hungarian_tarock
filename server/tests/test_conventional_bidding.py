"""Conventional bidding: invit and yielded game, after the examples in the rules."""

import pytest

from bots.strategy import decide_announcement, decide_bid, decide_call
from bots.view import build_view
from game_logic.bidding import BiddingManager
from models.bid import Bid, BidType
from models.game_state import GamePhase, invit_of, yielded_by
from tests.helpers import bidding_state, make_state

T, TWO, ONE, SOLO, HOLD, P = (BidType.THREE, BidType.TWO, BidType.ONE, BidType.SOLO, BidType.HOLD, BidType.PASS)
A, B, C, D = 0, 1, 2, 3


def auction(*bids, hands=None):
    """Play bids given as (seat, bid) from a deal where seat 0 speaks first."""
    gs = make_state(hands or ["skiz", "XXI", "I", "skiz"], dealer=3)
    gs.phase = GamePhase.BIDDING
    gs.current_turn = 0
    for seat, bid in bids:
        assert gs.current_turn == seat, f"seat {seat} is not to speak, seat {gs.current_turn} is"
        gs.place_bid(seat, bid)
    return gs


def finished(gs):
    assert gs.is_bidding_complete()
    gs.end_bidding()
    return gs


# ---- the examples ------------------------------------------------------------

def test_one_step_jump_invites_the_xix_and_a_later_jump_means_nothing():
    gs = finished(auction((A, T), (B, P), (C, P), (D, ONE), (A, SOLO), (D, P)))
    assert gs.invit() == {"by": D, "card": "XIX"}
    assert gs.declarer_position == A and gs.winning_bid.bid_type == SOLO
    assert gs.required_call() == "XIX"


def test_two_step_jump_invites_the_xviii_and_a_solo_can_be_held():
    gs = auction((A, T), (B, SOLO))
    # C and D never bid, so they cannot hold a solo: they pass by themselves
    assert gs.current_turn == A and not gs.is_bidding_complete()
    gs.place_bid(A, HOLD)
    finished(gs)
    assert gs.invit() == {"by": B, "card": "XVIII"}
    assert gs.declarer_position == A and gs.winning_bid.bid_type == SOLO
    assert gs.required_call() == "XVIII"


def test_opening_with_two_is_an_invit():
    gs = finished(auction((A, TWO), (B, P), (C, P), (D, ONE), (A, P)))
    assert gs.invit() == {"by": A, "card": "XIX"}
    assert gs.declarer_position == D and gs.required_call() == "XIX"


def test_jump_over_a_bid_one_could_have_held():
    gs = finished(auction((A, P), (B, T), (C, TWO), (D, P), (B, ONE), (C, HOLD), (B, P)))
    assert gs.invit() == {"by": B, "card": "XIX"}
    assert gs.declarer_position == C and gs.winning_bid.bid_type == ONE
    assert gs.required_call() == "XIX"


def test_solo_one_step_over_two_invites_the_xix():
    gs = auction((A, T), (B, TWO), (C, SOLO))
    assert gs.current_turn == A  # D passed by itself
    gs.place_bid(A, P)
    gs.place_bid(B, HOLD)
    finished(gs)
    assert gs.invit() == {"by": C, "card": "XIX"}
    assert gs.declarer_position == B and gs.required_call() == "XIX"


def test_nobody_takes_the_invit():
    gs = finished(auction((A, TWO), (B, ONE), (C, SOLO), (A, P), (B, P)))
    assert gs.invit() == {"by": A, "card": "XIX"}
    assert gs.declarer_position == C and gs.required_call() == "XIX"


def test_inviter_left_alone_calls_freely():
    gs = finished(auction((A, TWO), (B, P), (C, P), (D, P)))
    assert gs.invit() == {"by": A, "card": "XIX"}
    assert gs.declarer_position == A and gs.required_call() is None


def test_invit_taken_through_a_solo_in_between():
    gs = finished(auction((A, T), (B, P), (C, ONE), (D, SOLO), (A, HOLD)))
    assert gs.invit() == {"by": C, "card": "XIX"}
    assert gs.declarer_position == A and gs.required_call() == "XIX"


def test_yielded_game():
    gs = finished(auction((A, T), (B, P), (C, TWO), (D, P), (A, P)))
    assert gs.invit() is None and yielded_by(gs.bid_history) == A
    assert gs.declarer_position == C and gs.required_call() == "XX"


def test_no_convention_when_a_third_player_bids():
    gs = finished(auction((A, T), (B, TWO), (C, P), (D, ONE), (A, P), (B, P)))
    assert gs.invit() is None and yielded_by(gs.bid_history) is None
    assert gs.required_call() is None


def test_fourth_player_after_three_passes_gives_no_invit():
    gs = finished(auction((A, P), (B, P), (C, P), (D, ONE)))
    assert gs.invit() is None and gs.required_call() is None


def test_plain_auction_has_no_convention():
    gs = finished(auction((A, T), (B, TWO), (C, P), (D, P), (A, HOLD), (B, ONE), (A, P)))
    assert gs.invit() is None and yielded_by(gs.bid_history) is None


# ---- what a player may bid ---------------------------------------------------

WITH_XIX = "XXI XIX X IX VIII VII hK h10 s10"
NO_XIX = "XXI XVII X IX VIII VII hK h10 s10"
XX_BIG = "skiz XX X IX VIII VII hK h10 s10"
PAGAT_ONLY = "I XVII X IX VIII VII hK h10 s10"


def valid(gs, seat):
    return BiddingManager.get_valid_bid_types(gs.players[seat], gs.bid_history)


def test_jump_needs_the_invited_card():
    gs = auction(hands=[WITH_XIX, NO_XIX, PAGAT_ONLY, PAGAT_ONLY])
    # XIX but no XVIII; a solo straight away is no invit (nobody could take it)
    assert valid(gs, A) == [P, T, TWO, SOLO]
    gs = auction(hands=[NO_XIX, WITH_XIX, PAGAT_ONLY, PAGAT_ONLY])
    assert valid(gs, A) == [P, T, SOLO]
    ok, error = BiddingManager.can_player_bid(gs.players[A], TWO, gs.bid_history)
    assert not ok and "XIX" in error
    assert BiddingManager.invit_bids(auction(hands=[WITH_XIX] * 4).players[A], []) == {"two": "XIX"}


def test_after_an_invit_jumps_are_free():
    gs = auction((A, TWO), hands=[WITH_XIX, NO_XIX, PAGAT_ONLY, PAGAT_ONLY])
    assert valid(gs, B) == [P, ONE, SOLO]


def test_passing_a_three_to_a_lone_two_needs_xx_and_a_great_honour():
    gs = auction((A, T), (B, P), (C, TWO), (D, P), hands=[XX_BIG, NO_XIX, NO_XIX, NO_XIX])
    assert P in valid(gs, A)
    gs = auction((A, T), (B, P), (C, TWO), (D, P), hands=[NO_XIX, NO_XIX, NO_XIX, NO_XIX])
    # No XX: the pass is out. "One" would invite the XIX, "solo" the XVIII: only holding is left
    assert valid(gs, A) == [HOLD]


# ---- bots and hints ----------------------------------------------------------

def test_bot_invit_is_a_switch_that_is_off(monkeypatch):
    import bots.strategy as strategy
    gs = auction(hands=["XXI XIX X IX VIII VII hK h10 s10", "I", "skiz", "hK"])
    # Measured to lose points, so bots bid normally with such a hand…
    assert decide_bid(build_view(gs, A)).payload["bid_type"] == "three"
    # …but the tactic is there to be switched on
    monkeypatch.setattr(strategy, "TACTICS", set(strategy.ADOPTED) | {"invit_give"})
    d = decide_bid(build_view(gs, A))
    assert d.payload["bid_type"] == "two" and d.reason_key == "hint.bid.invit_give"


def test_bot_with_a_great_honour_takes_the_invit_and_the_inviter_steps_back():
    gs = auction((A, TWO), hands=["XXI XIX X IX VIII VII hK h10 s10", "skiz XX X V hK hQ sK sQ cK", "I", "hK"])
    d = decide_bid(build_view(gs, B))
    assert d.payload["bid_type"] == "one" and d.reason_key == "hint.bid.invit_accept"
    gs.place_bid(B, ONE)
    gs.place_bid(C, P)
    gs.place_bid(D, P)
    d = decide_bid(build_view(gs, A))
    assert d.payload["bid_type"] == "pass" and d.reason_key == "hint.bid.invit_taken"


def test_bot_yields_with_xx_and_great_honour_and_must_hold_without():
    gs = auction((A, T), (B, P), (C, TWO), (D, P), hands=[XX_BIG, NO_XIX, NO_XIX, NO_XIX])
    d = decide_bid(build_view(gs, A))
    assert d.payload["bid_type"] == "pass" and d.reason_key == "hint.bid.yield"
    # The pagát alone opened with eight tarokks; it would pass now, but may not
    weak = "I XVII XVI XV X IX VIII VII hK"
    gs = auction((A, T), (B, P), (C, TWO), (D, P), hands=[weak, NO_XIX, NO_XIX, NO_XIX])
    gs.players[A].hand = [c for c in gs.players[A].hand]
    d = decide_bid(build_view(gs, A))
    assert d.payload["bid_type"] == "hold"


def after_call(bids, hands, declarer_calls=True):
    gs = finished(auction(*bids, hands=hands))
    gs.phase = GamePhase.PARTNER_CALL
    gs.current_turn = gs.declarer_position
    return gs


def test_declarer_calls_the_invited_card_and_announces_trull_with_a_great_honour():
    hands = ["XXI XIX X IX VIII VII hK h10 s10", "skiz XX X V hK hQ sK sQ cK", "I II III IV dK dQ dJ cQ cJ", "hJ sJ cJ"]
    gs = after_call([(A, TWO), (B, ONE), (C, P), (D, P), (A, P)], hands)
    assert gs.declarer_position == B
    d = decide_call(build_view(gs, B))
    assert d.payload["tarokk_rank"] == "XIX" and d.reason_key == "hint.call.invit"
    gs.call_partner("XIX")
    assert gs.convention_partner() == A
    gs.start_announcement_phase()
    view = build_view(gs, B)
    assert view.partner_position == A          # the whole table knows
    assert build_view(gs, C).opponents() == {A, B}
    d = decide_announcement(view)
    assert "trull" in d.payload["announcement_types"]


def test_yielded_game_forces_the_xx():
    hands = [XX_BIG, "hK", "XXI XIX X V hK hQ sK sQ cK", "I"]
    gs = after_call([(A, T), (B, P), (C, TWO), (D, P), (A, P)], hands)
    d = decide_call(build_view(gs, C))
    assert d.payload["tarokk_rank"] == "XX" and d.reason_key == "hint.call.yielded"


def test_invit_with_the_pagat_alone_obliges_pagat_ulti():
    hands = ["I XIX X IX VIII VII hK h10 s10", "skiz XX X V hK hQ sK sQ cK", "XXI", "hK"]
    gs = after_call([(A, TWO), (B, ONE), (C, P), (D, P), (A, P)], hands)
    gs.call_partner("XIX")
    gs.start_announcement_phase()
    assert gs.owes_pagat_ulti(A) and not gs.owes_pagat_ulti(B)
    view = build_view(gs, A)
    assert view.must_ulti
    d = decide_announcement(view)
    assert "pagat_ultimo" in d.payload["announcement_types"]


# ---- through the actions -----------------------------------------------------

@pytest.mark.asyncio
async def test_accepted_invit_through_the_actions(monkeypatch):
    from tests.service_helpers import make_service, play_out_with_fallback, seed
    import bots.strategy as strategy
    from bots.strategy import decide
    from bots.view import build_view as view_of

    # Bots do not start an invit on their own: switch it on to get one
    monkeypatch.setattr(strategy, "TACTICS", set(strategy.ADOPTED) | {"invit_give"})

    for n in range(400):
        seed(n)
        service, manager, recorder = make_service(decide=lambda g, p: decide(view_of(g, p)))
        room = manager.create_room("s0", "Anna")
        room.fill_bots()
        room.players[0].is_ready = True
        await service.start_game(room)
        gs = room.game_state
        while gs.phase in (GamePhase.BIDDING, GamePhase.DISCARDING):
            seat = service.turn_position(room)
            await service.apply_decision(room, gs.get_player(seat), service.decide(gs, seat))
        if gs.phase == GamePhase.PARTNER_CALL and gs.required_call() and gs.invit():
            break
    else:
        pytest.fail("no accepted invit in 400 deals")

    invit, declarer = gs.invit(), gs.get_player(gs.declarer_position)
    assert invit["by"] != declarer.position
    # The inviter still holds the card, and no other card may be called
    assert any(c.is_tarokk() and c.rank == invit["card"] for c in gs.players[invit["by"]].hand)
    wrong = "XX" if invit["card"] != "XX" else "XIX"
    with pytest.raises(ValueError):
        await service.act_call_partner(room, declarer, wrong)
    await service.act_call_partner(room, declarer, invit["card"])
    assert gs.partner_position == invit["by"] and gs.convention_partner() == invit["by"]
    state = gs.to_dict()
    assert state["invit"] == invit and state["convention_partner"] == invit["by"]
    await play_out_with_fallback(service, room)
    assert gs.phase == GamePhase.GAME_END
