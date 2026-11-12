"""Rule corrections (design section 5.0)."""

import pytest

from game_logic.bidding import BiddingManager
from game_logic.final_scoring import calculate_final_score
from models.announcement import Announcement, AnnouncementType
from models.bid import Bid, BidType
from models.game_state import GamePhase
from validation.rules import validate_discard

from tests.helpers import bidding_state, card, cards, make_state


# --- 1. Hold -----------------------------------------------------------------

def test_holder_becomes_declarer():
    gs = bidding_state()
    gs.place_bid(0, BidType.THREE)
    gs.place_bid(1, BidType.TWO)
    gs.place_bid(2, BidType.PASS)
    gs.place_bid(3, BidType.PASS)
    gs.place_bid(0, BidType.HOLD)
    gs.place_bid(1, BidType.PASS)
    assert gs.is_bidding_complete()
    gs.end_bidding()
    assert gs.declarer_position == 0
    assert gs.winning_bid.bid_type == BidType.TWO
    assert gs.winning_bid.talon_cards == 2


def test_hold_not_legal_for_latest_bidder():
    gs = bidding_state()
    gs.place_bid(0, BidType.THREE)
    gs.place_bid(1, BidType.TWO)
    gs.place_bid(2, BidType.PASS)
    gs.place_bid(3, BidType.PASS)
    gs.place_bid(0, BidType.HOLD)
    # Seat 1 may not hold a hold: it must raise or pass
    assert BidType.HOLD not in BiddingManager.get_valid_bid_types(gs.players[1], gs.bid_history)
    with pytest.raises(ValueError):
        gs.place_bid(1, BidType.HOLD)
    gs.place_bid(1, BidType.ONE)
    # Now seat 0 may hold again
    assert BidType.HOLD in BiddingManager.get_valid_bid_types(gs.players[0], gs.bid_history)


def test_hold_needs_an_earlier_own_bid():
    gs = bidding_state()
    gs.place_bid(0, BidType.THREE)
    assert BidType.HOLD not in BiddingManager.get_valid_bid_types(gs.players[1], gs.bid_history)


# --- 2. A pass is final -------------------------------------------------------

def test_passed_player_not_asked_again():
    gs = bidding_state()
    gs.place_bid(0, BidType.THREE)
    gs.place_bid(1, BidType.PASS)
    gs.place_bid(2, BidType.TWO)
    gs.place_bid(3, BidType.PASS)
    assert gs.current_turn == 0
    gs.place_bid(0, BidType.ONE)
    # Seats 1 and 3 passed: the turn goes straight to seat 2
    assert gs.current_turn == 2
    with pytest.raises(ValueError):
        gs.place_bid(1, BidType.SOLO)


def test_auction_ends_when_one_left():
    gs = bidding_state()
    gs.place_bid(0, BidType.THREE)
    gs.place_bid(1, BidType.PASS)
    gs.place_bid(2, BidType.PASS)
    assert not gs.is_bidding_complete()
    gs.place_bid(3, BidType.PASS)
    assert gs.is_bidding_complete()
    gs.end_bidding()
    assert gs.declarer_position == 0


def test_last_seat_still_speaks_after_three_passes():
    gs = bidding_state()
    for seat in (0, 1, 2):
        gs.place_bid(seat, BidType.PASS)
    assert not gs.is_bidding_complete()
    assert gs.current_turn == 3
    gs.place_bid(3, BidType.THREE)
    assert gs.is_bidding_complete()


def test_all_pass_no_declarer():
    gs = bidding_state()
    for seat in range(4):
        gs.place_bid(seat, BidType.PASS)
    assert gs.is_bidding_complete()
    gs.end_bidding()
    assert gs.winning_bid is None and gs.declarer_position is None


def test_hold_bid_survives_dict_round_trip():
    held = Bid(player_position=0, bid_type=BidType.HOLD, game_value=2, talon_cards=2)
    again = Bid.from_dict(held.to_dict())
    assert again.game_value == 2 and again.talon_cards == 2


# --- 3 and 4. Announcement round ---------------------------------------------

def announcement_state(declarer=0):
    gs = make_state(["XX"] * 4)
    gs.declarer_position = declarer
    gs.start_announcement_phase()
    return gs


def test_fourth_seat_gets_announcement_turn():
    gs = announcement_state(declarer=0)
    for seat in (0, 1, 2):
        gs.player_pass_announcement(seat)
    assert not gs.is_announcement_phase_complete()
    assert gs.current_turn == 3
    gs.player_pass_announcement(3)
    assert gs.is_announcement_phase_complete()


def test_round_continues_after_an_announcement():
    gs = announcement_state(declarer=0)
    gs.player_pass_announcement(0)
    gs.player_pass_announcement(1)
    gs.player_pass_announcement(2)
    gs.make_announcement(Announcement(player_position=3, announcement_type=AnnouncementType.FOUR_KINGS))
    for seat in (0, 1):
        gs.player_pass_announcement(seat)
    assert not gs.is_announcement_phase_complete()
    gs.player_pass_announcement(2)
    assert gs.is_announcement_phase_complete()


def test_two_announcements_advance_turn_once():
    gs = announcement_state(declarer=1)
    gs.make_announcements(1, [
        Announcement(player_position=1, announcement_type=AnnouncementType.FOUR_KINGS),
        Announcement(player_position=1, announcement_type=AnnouncementType.DOUBLE_GAME),
    ])
    assert gs.current_turn == 2
    assert len(gs.announcements) == 2


# --- 5. What may not go into the skart ---------------------------------------

@pytest.mark.parametrize("code", ["XX", "skiz", "XXI", "I", "hK", "sK"])
def test_protected_cards_cannot_be_discarded(code):
    c = card(code)
    assert not c.can_be_discarded()
    ok, _ = validate_discard([c])
    assert not ok


def test_xix_and_suit_cards_can_be_discarded():
    assert card("XIX").can_be_discarded()
    assert card("hQ").can_be_discarded()
    ok, _ = validate_discard(cards("XIX hQ"))
    assert ok


# --- 6. Called tarokk in the skart -------------------------------------------

def alone_state():
    """Seat 0 is declarer holding XX; seat 2 discarded the XIX."""
    gs = make_state(["XX XVIII", "X", "IX", "VIII"])
    gs.declarer_position = 0
    gs.players[0].is_declarer = True
    gs.players[2].discard_pile.extend(cards("XIX"))
    return gs


def test_called_card_in_skart_declarer_alone():
    gs = alone_state()
    gs.call_partner("XIX")
    assert gs.declarer_alone is True
    assert gs.partner_position is None
    assert gs.called_card_discarded_by == 2
    assert not gs.players[2].is_partner


def test_declarer_discarding_own_called_card_needs_no_contra():
    gs = make_state(["XX", "X", "IX", "VIII"])
    gs.declarer_position = 0
    gs.players[0].discard_pile.extend(cards("XIX"))
    gs.call_partner("XIX")
    assert gs.declarer_alone is True
    assert gs.called_card_discarded_by is None


def test_obligatory_contra_applied_once_at_discarders_turn():
    gs = alone_state()
    gs.call_partner("XIX")
    gs.start_announcement_phase()
    assert gs.current_turn == 0
    assert gs.apply_obligatory_contra_if_due() is False
    gs.player_pass_announcement(0)
    gs.player_pass_announcement(1)
    assert gs.current_turn == 2
    assert gs.apply_obligatory_contra_if_due() is True
    assert gs.game_contra is True
    assert gs.apply_obligatory_contra_if_due() is False


def test_declarer_alone_hidden_until_contra():
    gs = alone_state()
    gs.call_partner("XIX")
    gs.phase = GamePhase.ANNOUNCEMENTS
    view = gs.to_dict(player_id=gs.players[1].id)
    assert view["declarer_alone"] is False
    assert "called_card_discarded_by" not in view
    gs.game_contra = True
    assert gs.to_dict(player_id=gs.players[1].id)["declarer_alone"] is True


def scoring_players(declarer_cards: str):
    gs = make_state()
    gs.players[0].tricks_won.extend(cards(declarer_cards))
    return gs.players


def test_scoring_without_partner():
    # Declarer alone with 50 card points wins against three
    players = scoring_players("hK dK sK cK skiz XXI I hQ dQ sQ cQ hC dC sC cC hJ dJ")
    result = calculate_final_score(
        players=players, declarer_position=0, partner_position=None,
        winning_bid=Bid(player_position=0, bid_type=BidType.THREE),
        announcements=[], trick_history=[],
    )
    assert result["winner"] == "declarer_team"
    assert result["player_scores"][0] == 50 + 3 * result["final_game_value"] + sum(
        3 * a["points"] for a in result["announcement_details"] if a["player_position"] == 0
    )
    assert sum(result["player_scores"].values()) == 200


def test_contra_doubles_game_value():
    players = scoring_players("hK dK sK cK skiz XXI I hQ dQ sQ cQ hC dC sC cC hJ dJ")
    kwargs = dict(
        players=players, declarer_position=0, partner_position=None,
        winning_bid=Bid(player_position=0, bid_type=BidType.TWO),
        announcements=[], trick_history=[],
    )
    plain = calculate_final_score(**kwargs)
    doubled = calculate_final_score(game_contra=True, **kwargs)
    assert doubled["final_game_value"] == 2 * plain["final_game_value"]
    assert doubled["game_contra"] is True
