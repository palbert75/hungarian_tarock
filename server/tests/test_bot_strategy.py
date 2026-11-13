"""One test per bot rule (design 5.2 and 5.3), each from a fixed hand."""

import dataclasses

from bots.counting import skiz_out, tarokks_out, xxi_out
from bots.strategy import (
    decide, decide_announcement, decide_bid, decide_call, decide_card, decide_discard,
)
from bots.view import SeatView, build_view
from models.announcement import Announcement, AnnouncementType
from models.bid import Bid, BidType
from models.game_state import GamePhase
from tests.helpers import card, cards, make_state


def bid_view(hand: str, valid, highest=None) -> SeatView:
    return SeatView(position=0, phase=GamePhase.BIDDING, hand=cards(hand), own_discards=[],
                    dealer_position=3, valid_bids=list(valid), highest_bid=highest)


def play_view(hand: str, trick=(), position=0, declarer=1, partner=None, i_am_partner=False,
              history=(), announcements=(), legal=None, alone=False) -> SeatView:
    hand_cards = cards(hand)
    current = [(seat, card(code)) for seat, code in trick]
    if legal is None:
        from validation.rules import get_legal_cards
        legal_cards = get_legal_cards(hand_cards, current[0][1].suit if current else None, not current)
    else:
        legal_cards = [c for c in hand_cards if c.rank in legal.split()]
    return SeatView(
        position=position, phase=GamePhase.PLAYING, hand=hand_cards, own_discards=[], dealer_position=3,
        declarer_position=declarer, called_rank="XX", partner_position=partner, i_am_partner=i_am_partner,
        declarer_alone=alone, announcements=list(announcements), current_trick=current,
        trick_history=[[(seat, card(code)) for seat, code in t] for t in history],
        legal_cards=list(legal_cards),
    )


def played(decision, view) -> str:
    c = next(c for c in view.hand if c.id == decision.payload["card_id"])
    return c.rank if c.is_tarokk() else f"{c.suit.value[0]}{c.rank}"


ALL = ["pass", "three", "two", "one", "solo"]

# ------------------------------------------------------------------ bidding


def test_no_honour_passes():
    d = decide_bid(bid_view("XX XIX X hK", ["pass"]))
    assert d.payload["bid_type"] == "pass" and d.reason_key == "hint.bid.no_honour"


def test_xxi_always_bids_lowest():
    d = decide_bid(bid_view("XXI II hK", ALL))
    assert d.payload["bid_type"] == "three" and d.reason_key == "hint.bid.xxi_always"


def test_xxi_holds_when_allowed_and_goes_up_to_one():
    assert decide_bid(bid_view("XXI II", ["pass", "hold", "one", "solo"], highest="two")).payload["bid_type"] == "hold"
    assert decide_bid(bid_view("XXI II", ["pass", "one", "solo"], highest="two")).payload["bid_type"] == "one"


def test_xxi_passes_when_only_solo_is_left():
    d = decide_bid(bid_view("XXI II", ["pass", "solo"], highest="one"))
    assert d.payload["bid_type"] == "pass" and d.reason_key == "hint.bid.xxi_stop_solo"
    # Holding a solo bid is a solo too
    assert decide_bid(bid_view("XXI II", ["pass", "hold"], highest="solo")).payload["bid_type"] == "pass"


def test_skiz_with_four_other_tarokks_passes():
    d = decide_bid(bid_view("skiz XX X V II hK", ALL))
    assert d.payload["bid_type"] == "pass" and d.reason_key == "hint.bid.skiz_strong_pass"
    assert d.reason_params == {"count": 4}


def test_skiz_with_three_other_tarokks_bids_up_to_two():
    assert decide_bid(bid_view("skiz XX X V hK", ALL)).payload["bid_type"] == "three"
    assert decide_bid(bid_view("skiz XX X V hK", ["pass", "two", "one", "solo"], "three")).payload["bid_type"] == "two"
    assert decide_bid(bid_view("skiz XX X V hK", ["pass", "one", "solo"], "two")).payload["bid_type"] == "pass"


def test_pagat_opens_only_with_eight_tarokks():
    eight = "I II III IV V VI VII VIII hK"
    seven = "I II III IV V VI VII hK hQ"
    assert decide_bid(bid_view(eight, ALL)).payload["bid_type"] == "three"
    d = decide_bid(bid_view(seven, ALL))
    assert d.payload["bid_type"] == "pass" and d.reason_key == "hint.bid.pagat_few_tarokks"


def test_pagat_does_not_overbid():
    eight = "I II III IV V VI VII VIII hK"
    assert decide_bid(bid_view(eight, ["pass", "one", "solo"], "two")).payload["bid_type"] == "pass"


def test_xxi_rule_comes_before_skiz_rule():
    # Skíz with a strong hand would pass, but the XXI always bids
    assert decide_bid(bid_view("skiz XXI XX X V II", ALL)).payload["bid_type"] == "three"


# -------------------------------------------------------------------- skart

def discard_view(hand: str, count: int) -> SeatView:
    return SeatView(position=0, phase=GamePhase.DISCARDING, hand=cards(hand), own_discards=[],
                    dealer_position=3, discard_count=count)


def test_discard_count_and_no_protected_card():
    view = discard_view("skiz XXI XX I hK dK sK cK II III hQ dQ", 3)
    d = decide_discard(view)
    chosen = [c for c in view.hand if c.id in d.payload["card_ids"]]
    assert len(chosen) == 3
    assert all(c.can_be_discarded() for c in chosen)
    # Two suit cards first, then the lowest tarokk
    assert sorted(c.rank for c in chosen) == ["II", "Q", "Q"]
    assert d.reason_key == "hint.discard.with_tarokks"


def test_discard_empties_short_kingless_suits_dearest_first():
    # Hearts has the king; diamonds (one card) and spades (two) do not
    view = discard_view("XX XIX XVIII hK hQ hJ dC sQ s10 X IX VIII", 3)
    d = decide_discard(view)
    chosen = {f"{c.suit.value[0]}{c.rank}" for c in view.hand if c.id in d.payload["card_ids"]}
    assert chosen == {"dC", "sQ", "s10"}
    assert d.reason_key == "hint.discard.suits"


# ------------------------------------------------------------- partner call

def call_view(hand: str) -> SeatView:
    return SeatView(position=0, phase=GamePhase.PARTNER_CALL, hand=cards(hand), own_discards=[],
                    dealer_position=3, declarer_position=0)


def test_call_is_xx():
    assert decide_call(call_view("XXI XIX X")).payload["tarokk_rank"] == "XX"


def test_call_highest_below_xx_not_held():
    assert decide_call(call_view("XXI XX XIX X")).payload["tarokk_rank"] == "XVIII"


# ------------------------------------------------------------ announcements

def announce_view(hand: str, partner=False, made=()) -> SeatView:
    everything = ["trull", "four_kings", "double_game", "volat", "pagat_ultimo", "xxi_catch"]
    return SeatView(position=2, phase=GamePhase.ANNOUNCEMENTS, hand=cards(hand), own_discards=[],
                    dealer_position=3, declarer_position=0, called_rank="XX", i_am_partner=partner,
                    valid_announcements=[a for a in everything if a not in made])


def test_partner_with_six_tarokks_announces_four_kings():
    d = decide_announcement(announce_view("XX X IX VIII VII VI hQ hJ h10", partner=True))
    assert d.action == "announce" and d.payload["announcement_types"] == ["four_kings"]


def test_partner_with_five_tarokks_does_not_announce_four_kings():
    d = decide_announcement(announce_view("XX X IX VIII VII hC hQ hJ h10", partner=True))
    assert d.action == "pass_announcement"


def test_partner_with_five_high_tarokks_announces_double_game():
    d = decide_announcement(announce_view("XX XIX XVIII XVII XIV hC hQ hJ h10", partner=True))
    assert d.payload["announcement_types"] == ["double_game"]


def test_xiii_is_not_above_xiii():
    d = decide_announcement(announce_view("XX XIX XVIII XVII XIII hC hQ hJ h10", partner=True))
    assert d.action == "pass_announcement"


def test_partner_rules_do_not_apply_to_others():
    d = decide_announcement(announce_view("XIX XVIII XVII XVI XV XIV hQ hJ h10", partner=False))
    assert d.action == "pass_announcement"


def test_bot_never_repeats_an_announcement():
    hand = "XX XIX XVIII XVII XVI XV hQ hJ h10"
    first = decide_announcement(announce_view(hand, partner=True))
    assert set(first.payload["announcement_types"]) == {"four_kings", "double_game"}
    again = decide_announcement(announce_view(hand, partner=True, made=("four_kings", "double_game")))
    assert again.action == "pass_announcement"


def test_trull_needs_all_three_honours():
    assert decide_announcement(announce_view("skiz XXI I XX X IX VIII hQ hJ")).payload["announcement_types"] == ["trull"]
    assert decide_announcement(announce_view("skiz XXI II XX X IX VIII hQ hJ")).action == "pass_announcement"


def test_never_volat_xxi_catch():
    d = decide_announcement(announce_view("skiz XXI XX XIX XVIII XVII XVI XV XIV"))
    assert d.action == "pass_announcement"


def test_pagat_ulti_needs_a_long_tarokk_hand():
    nine = "I II III IV V VI VII VIII IX"
    assert decide_announcement(announce_view(nine)).payload["announcement_types"] == ["pagat_ultimo"]
    assert decide_announcement(announce_view("I II III IV V VI VII hQ hJ")).action == "pass_announcement"


# ----------------------------------------------------------- defender leads

def test_defender_leads_tarokk_when_fellow_defender_plays_last():
    # I am seat 0, declarer 1, partner 2 (revealed): the fellow defender is seat 3 = last to play
    view = play_view("X V hQ h10 dJ", declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "V" and d.reason_key == "hint.lead.partner_last_tarokk"


def test_defender_leads_suit_when_fellow_defender_is_not_last():
    # Declarer 3 plays last; fellow defender is seat 1
    view = play_view("X V hQ h10 dJ", declarer=3, partner=2)
    d = decide_card(view)
    assert played(d, view) == "h10" and d.reason_key == "hint.lead.suit_protect_xxi"


def test_defender_leads_suit_before_partner_is_revealed():
    view = play_view("X V hQ h10 dJ", declarer=1, partner=None)
    d = decide_card(view)
    assert played(d, view) == "h10" and d.reason_key == "hint.lead.suit_protect_xxi"


def test_lead_rule_off_when_trull_announced():
    trull = Announcement(player_position=1, announcement_type=AnnouncementType.TRULL)
    view = play_view("X V hQ h10 dJ", declarer=1, partner=2, announcements=[trull])
    assert decide_card(view).reason_key == "hint.lead.long_suit"


def test_lead_rule_off_when_xxi_was_played():
    view = play_view("X V hQ h10 dJ", declarer=1, partner=2,
                     history=[[(0, "II"), (1, "XXI"), (2, "III"), (3, "IV")]])
    assert decide_card(view).reason_key == "hint.lead.defender_suit"


def test_lead_rule_off_when_i_hold_the_xxi():
    view = play_view("XXI V hQ h10 dJ", declarer=1, partner=2)
    assert decide_card(view).reason_key == "hint.lead.long_suit"


def test_declarer_draws_tarokks_but_not_with_xxi_while_skiz_is_out():
    # 20 tarokks seen (hand + history) leaves few out: the declarer has the upper hand
    history = [[(0, "II"), (1, "III"), (2, "IV"), (3, "V")],
               [(0, "VI"), (1, "VII"), (2, "VIII"), (3, "IX")],
               [(0, "X"), (1, "XI"), (2, "XII"), (3, "XIII")]]
    view = play_view("XXI XIX XVIII XVII hK", position=0, declarer=0, history=history)
    d = decide_card(view)
    assert played(d, view) == "XIX" and d.reason_key == "hint.lead.draw_tarokks"


# ---------------------------------------------------------------- following

def test_skiz_catches_an_opponents_xxi():
    view = play_view("skiz XX II", trick=[(3, "X"), (1, "XXI")], position=0, declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "skiz" and d.reason_key == "hint.follow.catch_xxi"


def test_skiz_does_not_catch_a_teammates_xxi():
    view = play_view("skiz XX II", trick=[(1, "X"), (3, "XXI")], position=0, declarer=1, partner=2)
    assert played(decide_card(view), view) != "skiz"


def test_xxi_is_not_played_while_skiz_is_out_and_an_opponent_follows():
    view = play_view("XXI XII III", trick=[(3, "X")], position=0, declarer=1, partner=2)
    assert played(decide_card(view), view) != "XXI"


def test_xxi_is_played_when_it_is_the_only_legal_card():
    view = play_view("XXI hK", trick=[(3, "X")], position=0, declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "XXI" and d.reason_key == "hint.follow.only_card"


def test_last_player_wins_with_the_lowest_winning_card():
    view = play_view("XX XII VIII", trick=[(1, "X"), (2, "VI"), (3, "hK")], position=0, declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "XII" and d.reason_key == "hint.follow.win_cheap"


def test_feeds_points_to_a_winning_teammate():
    # Seat 3 is my fellow defender and plays the king; I am last
    view = play_view("hQ hJ h10", trick=[(1, "h10"), (2, "hC"), (3, "hK")], position=0, declarer=1, partner=2)
    # Three tens do not exist, but the choice is what matters
    d = decide_card(view)
    assert played(d, view) == "hQ" and d.reason_key == "hint.follow.feed_teammate"


def test_pagat_goes_home_under_a_teammates_certain_trick():
    view = play_view("I V", trick=[(1, "X"), (2, "VI"), (3, "XX")], position=0, declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "I" and d.reason_key == "hint.follow.pagat_home"


def test_cannot_win_plays_low_and_keeps_the_pagat():
    view = play_view("I V III", trick=[(1, "XX")], position=0, declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "III" and d.reason_key == "hint.follow.low"


def test_ulti_announcer_keeps_the_pagat_and_draws_tarokks():
    ulti = Announcement(player_position=0, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("I XX XV hK", position=0, declarer=0, announcements=[ulti])
    d = decide_card(view)
    assert played(d, view) == "XV" and d.reason_key == "hint.lead.ulti_draw"


def test_defender_keeps_a_tarokk_against_an_announced_ulti():
    ulti = Announcement(player_position=1, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("XV hQ h10", position=0, declarer=1, partner=2, announcements=[ulti])
    d = decide_card(view)
    assert played(d, view) == "h10" and d.reason_key == "hint.lead.keep_tarokk_for_ulti"


# ----------------------------------------------------------------- counting

def test_tarokk_counting():
    view = play_view("XX X", trick=[(1, "XXI")], history=[[(0, "II"), (1, "skiz"), (2, "III"), (3, "IV")]])
    view.own_discards = cards("V")
    out = tarokks_out(view)
    assert 22 not in out and 21 not in out and 20 not in out and 5 not in out and 2 not in out
    assert 19 in out and 1 in out
    assert len(out) == 22 - 8
    assert not skiz_out(view) and not xxi_out(view)


# --------------------------------------------------------------- what a seat sees

def test_view_hides_hidden_info():
    gs = make_state(["XXI XIX X hK", "skiz II hQ", "I XX III", "IV V dK"], dealer=3)
    gs.talon = cards("sK sQ sC sJ s10 cK")
    gs.start_bidding()
    gs.declarer_position = 0
    gs.called_card_rank = "XX"
    gs.partner_position = 2          # the engine knows
    gs.partner_revealed = False      # the table does not
    gs.players[1].discard_pile = cards("cQ")
    gs.phase = GamePhase.PLAYING

    view = build_view(gs, 1)
    names = {f.name for f in dataclasses.fields(view)}
    assert "talon" not in names and "deck" not in names and "players" not in names
    assert [c.rank for c in view.hand] == ["skiz", "II", "Q"]
    assert [c.rank for c in view.own_discards] == ["Q"]
    assert view.partner_position is None and view.i_am_partner is False
    assert view.teammates() == set()

    # Every card the view carries is the seat's own
    own_ids = {c.id for c in gs.players[1].hand + gs.players[1].discard_pile}
    for name in names:
        value = getattr(view, name)
        if isinstance(value, list):
            for item in value:
                if hasattr(item, "points"):
                    assert item.id in own_ids, name

    # The holder of the called card knows it is the partner; the declarer does not know who
    assert build_view(gs, 2).i_am_partner is True
    assert build_view(gs, 2).teammates() == {0}
    assert build_view(gs, 0).teammates() == set()

    # Once the called card has shown, everybody knows
    gs.partner_revealed = True
    assert build_view(gs, 1).partner_position == 2
    assert build_view(gs, 1).teammates() == {3}
    assert build_view(gs, 0).teammates() == {2}


def test_declarer_alone_is_hidden_until_the_kontra():
    gs = make_state(["XXI X", "skiz II", "I III", "IV V"], dealer=3)
    gs.declarer_position = 0
    gs.declarer_alone = True
    gs.phase = GamePhase.ANNOUNCEMENTS
    assert build_view(gs, 1).declarer_alone is False
    gs.game_contra = True
    assert build_view(gs, 1).declarer_alone is True
    assert build_view(gs, 1).teammates() == {2, 3}


def test_decide_dispatches_by_phase():
    gs = make_state(["XXI XIX X hK", "skiz II hQ", "I XX III", "IV V dK"], dealer=3)
    gs.start_bidding()
    d = decide(build_view(gs, gs.current_turn))
    assert d.action == "bid"
    assert Bid(player_position=0, bid_type=BidType(d.payload["bid_type"]))


# ------------------------------------------------ the four-kings signal and other tactics

def test_declarer_answers_the_four_kings_signal_with_double_game():
    signal = Announcement(player_position=2, announcement_type=AnnouncementType.FOUR_KINGS)
    view = announce_view("skiz XX XV X IX VIII hK hQ dK", made=("four_kings",))
    view.position = 0
    view.announcements = [signal]
    # Off by default since a lost double game costs four times the game
    assert decide_announcement(view).action == "pass_announcement"
    import bots.strategy as S
    S.TACTICS.add("signal_double")
    try:
        _check_signal_double(view, signal)
    finally:
        S.TACTICS.discard("signal_double")


def _check_signal_double(view, signal):
    d = decide_announcement(view)
    assert d.payload["announcement_types"] == ["double_game"]
    assert d.reason_key == "hint.announce.double_after_signal"
    # Not without a great honour, and not without the signal
    weak = announce_view("XX XV X IX VIII VII hK hQ dK", made=("four_kings",))
    weak.position = 0
    weak.announcements = [signal]
    assert decide_announcement(weak).action == "pass_announcement"
    view.announcements = []
    assert decide_announcement(view).action == "pass_announcement"


def test_four_kings_signal_shows_the_table_who_the_partner_is():
    signal = Announcement(player_position=2, announcement_type=AnnouncementType.FOUR_KINGS)
    # Seat 0 defends, declarer 1; seat 2 signalled, so seat 3 is the fellow defender and plays last
    view = play_view("X V hQ h10 dJ", declarer=1, partner=None, announcements=[signal])
    d = decide(view)
    assert view.partner_position == 2
    assert played(d, view) == "V" and d.reason_key == "hint.lead.partner_last_tarokk"


def test_holder_of_the_xx_discards_cheap_cards():
    view = discard_view("XX XIX X IX hK hQ dC dJ sQ s10", 1)
    view.declarer_position = 1
    chosen = [c for c in view.hand if c.id in decide_discard(view).payload["card_ids"]]
    assert [(c.suit.value, c.rank) for c in chosen] == [("diamonds", "J")]
    # The declarer keeps the points for their own side
    view.declarer_position = 0
    chosen = [c for c in view.hand if c.id in decide_discard(view).payload["card_ids"]]
    assert [(c.suit.value, c.rank) for c in chosen] == [("diamonds", "C")]


def test_leads_the_suit_a_teammate_is_void_in():
    # Seat 3 (fellow defender) could not follow diamonds earlier
    history = [[(1, "dK"), (2, "dQ"), (3, "II"), (0, "d10")]]
    trull = Announcement(player_position=1, announcement_type=AnnouncementType.TRULL)
    view = play_view("hQ hJ h10 dJ", declarer=1, partner=2, history=history, announcements=[trull])
    assert played(decide_card(view), view) == "dJ"


def test_called_partner_with_great_honour_announces_trull():
    for hand in ("skiz X hK hQ hJ h10 dQ dJ d10", "XXI X hK hQ hJ h10 dQ dJ d10"):
        d = decide_announcement(announce_view(hand, partner=True))
        assert d.payload["announcement_types"] == ["trull"] and d.reason_key == "hint.announce.trull_partner"


def test_partner_without_great_honour_or_non_partner_does_not_announce_trull():
    assert decide_announcement(announce_view("I X hK hQ hJ h10 dQ dJ d10", partner=True)).action == "pass_announcement"
    assert decide_announcement(announce_view("skiz X hK hQ hJ h10 dQ dJ d10")).action == "pass_announcement"


# ---- the skíz waits for the XXI; trump hard when a king is at stake

def test_skiz_holder_leads_a_kingless_suit_not_a_tarokk():
    view = play_view("skiz XVIII X hQ h10 dK dJ", declarer=0, partner=2)
    d = decide_card(view)
    assert d.reason_key == "hint.lead.skiz_suit" and played(d, view) == "h10"


def test_skiz_holder_with_the_xxi_does_not_wait():
    view = play_view("skiz XXI XVIII X hQ h10", declarer=0, partner=2)
    assert not decide_card(view).reason_key.startswith("hint.lead.skiz")


def test_skiz_holder_does_not_wait_once_the_xxi_is_played():
    view = play_view("skiz XVIII X hQ h10", declarer=0, partner=2,
                     history=[[(0, "II"), (1, "XXI"), (2, "III"), (3, "IV")]])
    assert not decide_card(view).reason_key.startswith("hint.lead.skiz")


def test_defender_leads_suit_once_the_skiz_is_played():
    view = play_view("X V hQ h10 dJ", declarer=1, partner=2,
                     history=[[(0, "II"), (1, "skiz"), (2, "III"), (3, "IV")]])
    d = decide_card(view)
    assert d.reason_key == "hint.lead.defender_suit" and not d.payload["card_id"].startswith("tarokk")


def test_waiting_skiz_sheds_a_high_tarokk_without_winning():
    view = play_view("skiz XIV X hQ", trick=[(3, "XV")], declarer=0, partner=2)
    d = decide_card(view)
    assert d.reason_key == "hint.follow.skiz_duck_high" and played(d, view) == "XIV"


def test_waiting_skiz_still_catches_the_xxi():
    view = play_view("skiz XIV X hQ", trick=[(3, "XXI")], declarer=0, partner=2)
    assert played(decide_card(view), view) == "skiz"


def test_trump_hard_on_teammates_suit_lead_when_an_opponent_follows():
    view = play_view("XIX X V dQ", trick=[(3, "hK")], declarer=0, partner=3)
    d = decide_card(view)
    assert d.reason_key == "hint.follow.hit_hard" and played(d, view) == "XIX"


def test_trump_hard_on_an_opponents_king_when_not_last():
    view = play_view("XIX X V dQ", trick=[(2, "hK")], declarer=0, partner=3)
    d = decide_card(view)
    assert d.reason_key == "hint.follow.hit_hard" and played(d, view) == "XIX"


def test_last_to_play_still_wins_cheaply():
    view = play_view("XIX X V dQ", trick=[(1, "hK"), (2, "h10"), (3, "hQ")], declarer=0, partner=3)
    d = decide_card(view)
    assert d.reason_key == "hint.follow.win_cheap" and played(d, view) == "V"


def test_waiting_skiz_does_not_trump_hard():
    view = play_view("skiz XIX X dQ", trick=[(3, "hK")], declarer=0, partner=3)
    d = decide_card(view)
    assert d.reason_key == "hint.follow.skiz_forced" and played(d, view) == "X"


# ---- tactics from the advice text

def test_pagat_says_two_over_three_from_the_seat_before():
    view = bid_view("I X IX hK hQ dQ dJ sJ c10", ["pass", "two"], highest="three")
    view.bid_history = [Bid(player_position=3, bid_type=BidType.THREE)]
    d = decide_bid(view)
    assert d.payload["bid_type"] == "two" and d.reason_key == "hint.bid.two_over_three"


def test_pagat_does_not_overbid_a_three_from_elsewhere():
    view = bid_view("I X IX hK hQ dQ dJ sJ c10", ["pass", "two"], highest="three")
    view.bid_history = [Bid(player_position=2, bid_type=BidType.THREE), Bid(player_position=3, bid_type=BidType.PASS)]
    assert decide_bid(view).payload["bid_type"] == "pass"


def test_skiz_without_xxi_discards_high_tarokks():
    view = discard_view("skiz XIX XVII XII X VII V III II hQ dJ", 2)
    d = decide_discard(view)
    chosen = sorted(c.rank for c in view.hand if c.id in d.payload["card_ids"])
    assert chosen == ["XIX", "XVII"] and d.reason_key == "hint.discard.skiz_weaken"


def test_skiz_with_six_tarokks_discards_suits_as_usual():
    view = discard_view("skiz XIX XVII XII X VII hQ dJ sJ c10 hK", 2)
    assert decide_discard(view).reason_key == "hint.discard.suits"


def kontra_view(hand: str, kind: AnnouncementType, by: int, declarer=1) -> SeatView:
    view = announce_view(hand)
    view.position, view.declarer_position = 0, declarer
    view.announcements = [Announcement(player_position=by, announcement_type=kind)]
    return view


def test_kontra_four_kings_with_long_high_tarokks():
    d = decide_announcement(kontra_view("XIX XVIII X IX VIII VII hQ hJ h10", AnnouncementType.FOUR_KINGS, by=1))
    assert d.action == "contra" and d.payload == {"announcement_type": "four_kings"}


def test_no_kontra_with_a_short_hand_or_against_an_unknown_side():
    assert decide_announcement(
        kontra_view("XIX XVIII X hK hQ hJ h10 dQ dJ", AnnouncementType.FOUR_KINGS, by=1)).action == "pass_announcement"
    # Seat 2 is not known to be an opponent
    assert decide_announcement(
        kontra_view("XIX XVIII X IX VIII VII VI hJ h10", AnnouncementType.PAGAT_ULTIMO, by=2)).action == "pass_announcement"


def test_kontra_pagat_ulti_with_seven_tarokks():
    d = decide_announcement(kontra_view("XIX XVIII X IX VIII VII VI hJ h10", AnnouncementType.PAGAT_ULTIMO, by=1))
    assert d.action == "contra" and d.reason_key == "hint.announce.kontra_ulti"


def test_drive_high_tarokk_for_the_waiting_skiz_behind_me():
    # Seat 3 (my teammate, last to play when I lead) threw the XVII under the XVIII
    history = [[(1, "XVIII"), (2, "IV"), (3, "XVII"), (0, "II")]]
    view = play_view("XIX XII V hQ h10", declarer=1, partner=2, history=history)
    d = decide_card(view)
    assert d.reason_key == "hint.lead.drive_for_skiz" and played(d, view) == "XIX"


def test_catch_the_pagat_when_my_side_announced_trull():
    trull = Announcement(player_position=0, announcement_type=AnnouncementType.TRULL)
    view = play_view("skiz XXI XIX XII X V hQ", declarer=0, partner=2, announcements=[trull])
    d = decide_card(view)
    assert d.reason_key == "hint.lead.catch_pagat" and played(d, view) in ("skiz", "XXI")


def test_long_hand_leaves_a_cheap_early_trick_to_the_teammate_behind():
    view = play_view("XIX XVII XII X VIII V III hQ", trick=[(3, "IX")], declarer=0, partner=1)
    d = decide_card(view)
    assert d.reason_key == "hint.follow.leave_to_short_hand" and played(d, view) == "III"


def test_long_hand_still_takes_a_king():
    view = play_view("XIX XVII XII X VIII V III dQ", trick=[(3, "hK")], declarer=0, partner=1)
    assert decide_card(view).reason_key != "hint.follow.leave_to_short_hand"


def test_ulti_teammate_keeps_the_smallest_tarokk():
    ulti = Announcement(player_position=2, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("XII V III hQ", trick=[(1, "XVIII")], declarer=0, partner=2, announcements=[ulti])
    assert played(decide_card(view), view) == "V"
    lead = play_view("XII V III hQ", declarer=0, partner=2, announcements=[ulti])
    assert played(decide_card(lead), lead) == "V"


def test_defender_with_the_skiz_never_gets_the_protect_xxi_advice():
    # Fellow defender (seat 3) would play last: without the skíz this is a tarokk lead
    without = play_view("XVIII X V hQ h10 dJ", declarer=1, partner=2)
    assert decide_card(without).reason_key == "hint.lead.partner_last_tarokk"
    for partner in (2, 3):  # teammate last, or not last
        view = play_view("skiz XVIII X V hQ h10 dJ", declarer=1, partner=partner)
        d = decide_card(view)
        assert d.reason_key == "hint.lead.skiz_suit" and not d.payload["card_id"].startswith("tarokk")
    # Even with the waiting rule switched off, the protect-the-XXI rule does not apply to the skíz
    import bots.strategy as S
    saved = set(S.TACTICS)
    try:
        S.TACTICS.discard("skiz_hunt")
        view = play_view("skiz XVIII X V hQ h10 dJ", declarer=1, partner=2)
        assert decide_card(view).reason_key not in ("hint.lead.partner_last_tarokk", "hint.lead.suit_protect_xxi")
    finally:
        S.TACTICS.clear(); S.TACTICS.update(saved)


def test_declarer_with_both_great_honours_announces_trull():
    hand = "skiz XXI XIX XII IX hQ hJ sK sJ"
    assert decide_announcement(announce_view(hand)).action == "pass_announcement"  # not the declarer
    d = decide_announcement(dataclasses.replace(announce_view(hand), position=0))
    assert d.payload["announcement_types"] == ["trull"] and d.reason_key == "hint.announce.trull_two"
