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
    # Double game first; four kings waits a turn so the declarer can answer
    first = decide_announcement(announce_view(hand, partner=True))
    assert first.payload["announcement_types"] == ["double_game"]
    second = decide_announcement(announce_view(hand, partner=True, made=("double_game",)))
    assert second.payload["announcement_types"] == ["four_kings"]
    again = decide_announcement(announce_view(hand, partner=True, made=("four_kings", "double_game")))
    assert again.action == "pass_announcement"


def test_declarers_side_says_at_most_two_things_a_turn_and_trull_first():
    # Skíz and XXI, seven tarokks, five above the XIII: trull, double game and four kings all apply
    hand = "skiz XXI XX XIX XVIII X IX hQ hJ"
    first = decide_announcement(announce_view(hand, partner=True))
    assert first.payload["announcement_types"] == ["trull", "double_game"]
    second = decide_announcement(announce_view(hand, partner=True, made=("trull", "double_game")))
    assert second.payload["announcement_types"] == ["four_kings"]


def test_pagat_ulti_is_said_last():
    # Skíz, XXI, pagát, nine tarokks, five above the XIII: trull and double game go first, the ulti next turn
    hand = "skiz XXI I XX XIX XVIII X IX VIII"
    first = decide_announcement(announce_view(hand, partner=True))
    assert first.payload["announcement_types"] == ["trull", "double_game"]
    second = decide_announcement(announce_view(hand, partner=True, made=("trull", "double_game")))
    assert second.payload["announcement_types"] == ["pagat_ultimo"]


def test_no_four_kings_from_a_pagat_ulti_hand_or_beside_the_tarokk_count():
    # Pagát and eight tarokks: the bot wants to hear four kings from its partner instead
    ulti_hand = announce_view("I II III IV V VI VII XX hQ", partner=True)
    assert decide_announcement(ulti_hand).action == "pass_announcement"
    # Eight tarokks declared (trull was called): the count already says "long hand"
    trull = Announcement(player_position=0, announcement_type=AnnouncementType.TRULL)
    counted = announce_view("II III IV V VI VII VIII XX hQ", partner=True, made=("trull",))
    counted.announcements = [trull]
    counted.valid_announcements.append("eight_tarokks")
    assert decide_announcement(counted).payload["announcement_types"] == ["eight_tarokks"]


def as_declarer(view):
    return dataclasses.replace(view, position=0)


def test_declarer_with_all_three_honours_announces_trull():
    d = decide_announcement(as_declarer(announce_view("skiz XXI I XX X IX VIII hQ hJ")))
    assert d.payload["announcement_types"] == ["trull"]


def test_defenders_do_not_announce():
    """Only the declarer's side announces, so an announcement shows who is with whom."""
    assert decide_announcement(announce_view("skiz XXI I XX X IX VIII hQ hJ")).action == "pass_announcement"
    assert decide_announcement(announce_view("I II III IV V VI VII VIII IX")).action == "pass_announcement"


def test_never_volat_xxi_catch():
    d = decide_announcement(announce_view("skiz XXI XX XIX XVIII XVII XVI XV XIV"))
    assert d.action == "pass_announcement"


def test_pagat_ulti_needs_a_long_tarokk_hand():
    # The XXI is there so that this is not a bid on the pagát alone (that one always says ulti)
    nine = "I II III IV V VI VII VIII XXI"
    assert decide_announcement(as_declarer(announce_view(nine))).payload["announcement_types"] == ["pagat_ultimo"]
    assert decide_announcement(as_declarer(announce_view("I II III IV V VI XXI hQ hJ"))).action == "pass_announcement"


def test_declarer_with_eight_tarokks_announces_ulti_only_after_the_partners_four_kings():
    eight = "I II III IV XVII XVIII XIX XXI hQ"
    alone = as_declarer(announce_view(eight))
    assert decide_announcement(alone).action == "pass_announcement"
    kings = Announcement(player_position=2, announcement_type=AnnouncementType.FOUR_KINGS)
    after = dataclasses.replace(alone, announcements=[kings],
                                valid_announcements=[a for a in alone.valid_announcements if a != "four_kings"])
    assert decide_announcement(after).payload["announcement_types"] == ["pagat_ultimo"]


def test_partner_with_eight_tarokks_announces_ulti_only_after_the_declarers_four_kings():
    eight = "I II III IV V XVII XVIII XIX hQ"
    partner = announce_view(eight, partner=True)
    assert decide_announcement(partner).action == "pass_announcement"
    # The declarer's tarokk count says the same as four kings
    counted = dataclasses.replace(partner, tarokk_declarations={0: 8})
    assert decide_announcement(counted).payload["announcement_types"] == ["pagat_ultimo"]
    kings = Announcement(player_position=0, announcement_type=AnnouncementType.FOUR_KINGS)
    after = dataclasses.replace(partner, announcements=[kings],
                                valid_announcements=[a for a in partner.valid_announcements if a != "four_kings"])
    assert "pagat_ultimo" in decide_announcement(after).payload["announcement_types"]
    nine = announce_view("I II III IV V VI XVII XVIII XIX", partner=True)
    assert "pagat_ultimo" in decide_announcement(nine).payload["announcement_types"]


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
    assert decide_card(view).reason_key == "hint.lead.trull_suit"


def test_lead_rule_off_when_xxi_was_played():
    view = play_view("X V hQ h10 dJ", declarer=1, partner=2,
                     history=[[(0, "II"), (1, "XXI"), (2, "III"), (3, "IV")]])
    assert decide_card(view).reason_key == "hint.lead.defender_suit"


def test_with_trull_called_every_trick_is_fought_for():
    trull = Announcement(player_position=1, announcement_type=AnnouncementType.TRULL)
    # My fellow defender (seat 3) wins with the XV, but the declarer still plays: overtake with my best card
    view = play_view("XX X hQ", trick=[(3, "XV")], position=0, declarer=1, partner=2, announcements=[trull])
    d = decide_card(view)
    assert played(d, view) == "XX" and d.reason_key == "hint.follow.trull_win"
    # Without trull the same hand saves its tarokks
    calm = play_view("XX X hQ", trick=[(3, "XV")], position=0, declarer=1, partner=2)
    assert played(decide_card(calm), calm) == "X"
    # An opponent wins a trick worth nothing: take it all the same
    view = play_view("XX X hQ", trick=[(2, "V")], position=0, declarer=1, partner=2, announcements=[trull])
    d = decide_card(view)
    assert played(d, view) == "XX" and d.reason_key == "hint.follow.trull_win"
    # Last to play: the cheapest card that wins is enough
    view = play_view("XX X hQ", trick=[(1, "VII"), (2, "VI"), (3, "V")], position=0, declarer=1, partner=2,
                     announcements=[trull])
    d = decide_card(view)
    assert played(d, view) == "X" and d.reason_key == "hint.follow.trull_win"
    # My team holds the trick for certain: nothing to add
    view = play_view("XX X hQ", trick=[(1, "V"), (2, "VI"), (3, "XV")], position=0, declarer=1, partner=2,
                     announcements=[trull])
    assert decide_card(view).reason_key != "hint.follow.trull_win"


def test_with_trull_called_the_skiz_is_played_like_any_high_tarokk():
    # Problem report 20261116-215007: the declarer (seat 1) called trull, their partner (seat 0) leads
    # the VI, and the declarer holds only the skíz and the XIII. The XIII is lost to the XIV:
    # with trull called the skíz is not saved for a rich trick, it takes this one.
    trull = Announcement(player_position=1, announcement_type=AnnouncementType.TRULL)
    history = [[(3, "c10"), (0, "cK"), (1, "cJ"), (2, "I")],
               [(2, "dJ"), (3, "dK"), (0, "II"), (1, "dQ")],
               [(0, "V"), (1, "XXI"), (2, "VII"), (3, "IV")],
               [(1, "III"), (2, "XVII"), (3, "VIII"), (0, "XVIII")]]
    view = play_view("skiz XIII d10 hK hC", trick=[(0, "VI")], position=1, declarer=1, partner=0,
                     history=history, announcements=[trull])
    d = decide_card(view)
    assert played(d, view) == "skiz" and d.reason_key == "hint.follow.trull_win"
    # A tarokk nobody can beat still goes before the skíz
    view = play_view("skiz XXI d10 hK hC", trick=[(0, "VI")], position=1, declarer=1, partner=0,
                     announcements=[trull])
    assert played(decide_card(view), view) == "XXI"
    # Without trull the skíz still waits for a trick worth a king
    calm = play_view("skiz XIII d10 hK hC", trick=[(0, "VI")], position=1, declarer=1, partner=0, history=history)
    assert played(decide_card(calm), calm) == "XIII"


def test_with_trull_called_no_hard_tarokk_between_the_declarer_and_their_partner():
    # Problem report 20261115-203056: the declarer (seat 0) leads the VII, I am seat 1, the partner
    # (seat 2, known by the trull they announced) plays next and my fellow defender last.
    # The partner has to play high anyway: the XVIII would only be lost to the XX.
    trull = Announcement(player_position=2, announcement_type=AnnouncementType.TRULL)
    view = play_view("XVIII XIV IX VIII VI sK sC", trick=[(0, "VII")], position=1, declarer=0,
                     announcements=[trull])
    d = decide_card(view)
    assert played(d, view) == "VIII" and d.reason_key != "hint.follow.trull_win"
    # The same once the partner has shown the called card
    shown = play_view("XVIII XIV IX VIII VI sK sC", trick=[(0, "VII")], position=1, declarer=0, partner=2)
    shown.announcements = [Announcement(player_position=0, announcement_type=AnnouncementType.TRULL)]
    assert played(decide_card(shown), shown) == "VIII"
    # The partner sits last instead: the rule of the best card stands
    other = play_view("XVIII XIV IX VIII VI sK sC", trick=[(0, "VII")], position=1, declarer=0,
                      announcements=[Announcement(player_position=3, announcement_type=AnnouncementType.TRULL)])
    d = decide_card(other)
    assert played(d, other) == "XVIII" and d.reason_key == "hint.follow.trull_win"
    # A tarokk nobody can beat is still played: it holds the trick
    out_high = [[(0, "skiz"), (1, "II"), (2, "XXI"), (3, "III")], [(0, "XX"), (1, "IV"), (2, "XIX"), (3, "V")]]
    master = play_view("XVIII XIV IX VIII VI sK sC", trick=[(0, "VII")], position=1, declarer=0,
                       announcements=[trull], history=out_high)
    d = decide_card(master)
    assert played(d, master) == "XVIII" and d.reason_key == "hint.follow.trull_win"


def test_lead_rule_off_when_i_hold_the_xxi():
    view = play_view("XXI V hQ h10 dJ", declarer=1, partner=2)
    assert decide_card(view).reason_key == "hint.lead.xxi_suit"


def test_declarer_draws_tarokks_but_not_with_xxi_while_skiz_is_out():
    # 20 tarokks seen (hand + history) leaves few out: the declarer has the upper hand
    history = [[(0, "II"), (1, "III"), (2, "IV"), (3, "V")],
               [(0, "VI"), (1, "VII"), (2, "VIII"), (3, "IX")],
               [(0, "X"), (1, "XI"), (2, "XII"), (3, "XIII")]]
    # Partner not shown yet: a small tarokk, so the partner can answer with the called card
    view = play_view("XXI XIX XVIII XVII hK", position=0, declarer=0, history=history)
    d = decide_card(view)
    assert played(d, view) == "XVII" and d.reason_key == "hint.lead.xxi_find_partner"
    # Partner known and more tarokks than the skíz's hand can answer: high ones, never the XXI
    view = play_view("XXI XIX XVIII XVII hK", position=0, declarer=0, partner=2, history=history)
    d = decide_card(view)
    assert played(d, view) == "XIX" and d.reason_key == "hint.lead.xxi_drive_skiz"


def test_xxi_holder_on_the_callers_team_leads_its_shortest_suit_otherwise():
    # Partner unknown and only two tarokks beside the XXI: no tarokk lead
    view = play_view("XXI X V hQ hJ h10 dJ", position=0, declarer=0)
    d = decide_card(view)
    assert played(d, view) == "dJ" and d.reason_key == "hint.lead.xxi_short_suit"
    # Partner known, but far too few tarokks to run the skíz dry
    view = play_view("XXI X V IV hQ hJ h10 dJ", position=0, declarer=0, partner=2)
    d = decide_card(view)
    assert played(d, view) == "dJ" and d.reason_key == "hint.lead.xxi_short_suit"
    # A teammate's trull beside my XXI shows the skíz is theirs: the usual tarokk lead again
    trull = Announcement(player_position=2, announcement_type=AnnouncementType.TRULL)
    view = play_view("XXI X V IV hQ hJ h10 dJ", position=0, declarer=0, partner=2, announcements=[trull])
    assert decide_card(view).reason_key.startswith("hint.lead.d")


def test_xxi_goes_home_when_the_player_after_me_must_follow_suit_with_the_king():
    # The owner's report: my partner led a heart without its king, seat 1 trumped, I have no
    # heart: the king is with seat 3, who has to follow suit and cannot put the skíz on the XXI
    first = [[(0, "XX"), (1, "III"), (2, "II"), (3, "XIX")]]
    view = play_view("XXI XVIII XIV IV sK sQ sJ", trick=[(0, "hQ"), (1, "VI")], position=2, declarer=2,
                     partner=0, history=first)
    d = decide_card(view)
    assert played(d, view) == "XXI" and d.reason_key == "hint.follow.xxi_escape_king"
    # Seat 1 followed suit: the king can be there or with seat 3, so the XXI still ducks
    view = play_view("XXI XVIII XIV IV sK sQ sJ", trick=[(0, "hQ"), (1, "hJ")], position=2, declarer=2,
                     partner=0, history=first)
    assert played(decide_card(view), view) != "XXI"
    # Led by an opponent: no convention to read
    view = play_view("XXI XVIII XIV IV sK sQ sJ", trick=[(3, "hQ"), (0, "hJ"), (1, "VI")], position=2,
                     declarer=2, partner=0, history=first)
    assert played(decide_card(view), view) == "XXI"  # last to play, the old rule
    view = play_view("XXI XVIII XIV IV sK sQ sJ", trick=[(1, "hQ")], position=2, declarer=2,
                     partner=0, history=first)
    assert played(decide_card(view), view) != "XXI"


def test_caller_team_leads_a_suit_without_its_king_or_the_king_itself():
    # XXI at risk, partner known: diamonds are shortest but I hold their king, so the heart goes
    view = play_view("XXI II dK dJ hQ hJ h10", position=1, declarer=1, partner=3)
    d = decide_card(view)
    assert played(d, view) == "h10" and d.reason_key == "hint.lead.xxi_short_suit"
    # A king in every suit I hold: lead the king
    view = play_view("XXI II dK dJ", position=1, declarer=1, partner=3)
    assert played(decide_card(view), view) == "dK"


def test_xxi_escapes_when_nobody_dangerous_plays_after_me():
    # Last to play, the skíz is not in the trick
    view = play_view("XXI X hQ", trick=[(1, "V"), (2, "VI"), (3, "VII")], position=0, declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "XXI" and d.reason_key == "hint.follow.xxi_escape"
    # Only my teammate still plays after me
    view = play_view("XXI X hQ", trick=[(2, "V"), (3, "VI")], position=0, declarer=0, partner=1)
    d = decide_card(view)
    assert played(d, view) == "XXI" and d.reason_key == "hint.follow.xxi_escape"


def test_xxi_holder_stays_out_of_the_lead_while_an_opponent_plays_after():
    # An opponent still plays: the XXI stays, and so does the XX that would win the lead
    view = play_view("XXI XX IV hQ", trick=[(3, "X")], position=0, declarer=1, partner=2)
    d = decide_card(view)
    assert played(d, view) == "IV" and d.reason_key == "hint.follow.xxi_duck"


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
    view = play_view("I V IV", trick=[(1, "X"), (2, "VI"), (3, "XX")], position=0, declarer=1, partner=2)
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


def test_ulti_announcer_without_tarokks_to_draw_leads_a_king():
    mine = Announcement(player_position=0, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("I hQ h10 dK dJ", position=0, declarer=0, partner=2, announcements=[mine])
    d = decide_card(view)
    assert played(d, view) == "dK" and d.reason_key == "hint.lead.ulti_keep_pagat"
    # No king: any suit card
    view = play_view("I hQ h10 dJ", position=0, declarer=0, partner=2, announcements=[mine])
    d = decide_card(view)
    assert played(d, view) == "h10" and d.reason_key == "hint.lead.ulti_keep_pagat"


def test_skiz_goes_when_the_last_tarokks_out_must_fall_under_it():
    # 16 tarokks gone in four tricks; with my skíz, XIX and XVIII only the XXI, the XX and the pagát are out
    ranks = "II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII".split()
    history = [[(seat, ranks[4 * t + seat]) for seat in range(4)] for t in range(4)]
    # Leading: three tarokks out, three players follow
    view = play_view("skiz XIX XVIII hQ", position=0, declarer=1, partner=2, history=history)
    d = decide_card(view)
    assert played(d, view) == "skiz" and d.reason_key == "hint.lead.skiz_force"
    # Following a tarokk lead: the XX lies there, two tarokks out, two players still to play
    view = play_view("skiz XIX XVIII hQ", trick=[(3, "XX")], position=0, declarer=1, partner=2, history=history)
    d = decide_card(view)
    assert played(d, view) == "skiz" and d.reason_key == "hint.follow.skiz_force"
    # Early in the hand plenty of tarokks are out: keep waiting
    view = play_view("skiz X hQ h10", trick=[(3, "XX")], position=0, declarer=1, partner=2)
    assert decide_card(view).reason_key != "hint.follow.skiz_force"


def test_enemy_team_leads_a_suit_without_its_king_against_four_kings_or_double_game():
    for kind in (AnnouncementType.FOUR_KINGS, AnnouncementType.DOUBLE_GAME):
        bid = Announcement(player_position=2, announcement_type=kind)
        # Hearts are my longest suit but I hold their king: lead the diamond
        view = play_view("X V hK hQ hJ h10 dJ", position=0, declarer=3, partner=2, announcements=[bid])
        d = decide_card(view)
        assert played(d, view) == "dJ" and d.reason_key == "hint.lead.kings_suit"
    # Saving a teammate's XXI still comes first: seat 3, my teammate, plays last
    view = play_view("X V hK hQ dJ", position=0, declarer=1, partner=2, announcements=[bid])
    assert decide_card(view).reason_key == "hint.lead.partner_last_tarokk"
    # The caller's team keeps leading tarokks
    view = play_view("X V hK hQ dJ", position=1, declarer=1, partner=2, announcements=[bid])
    assert played(decide_card(view), view) == "V"


SEVEN_TRICKS = [
    [(2, "d10"), (3, "dQ"), (0, "IV"), (1, "dK")], [(0, "cJ"), (1, "XVIII"), (2, "cK"), (3, "XIX")],
    [(3, "II"), (0, "VI"), (1, "VII"), (2, "V")], [(1, "h10"), (2, "hK"), (3, "hC"), (0, "XI")],
    [(0, "sQ"), (1, "sK"), (2, "XIV"), (3, "III")], [(2, "dJ"), (3, "XV"), (0, "XII"), (1, "XXI")],
    [(1, "X"), (2, "XVII"), (3, "VIII"), (0, "XX")],
]


def test_pagat_goes_in_the_second_last_trick_when_a_tarokk_stays_out_for_the_last():
    # The owner's report: skíz, XVI and IX are out, two players still play to this trick
    view = play_view("XIII I", trick=[(0, "s10")], position=1, declarer=1, partner=0, history=SEVEN_TRICKS)
    d = decide_card(view)
    assert played(d, view) == "I" and d.reason_key == "hint.follow.pagat_drop"
    # Two tarokks out (skíz, IX) and two players still to play: both can fall now, the pagát waits
    late = SEVEN_TRICKS[:6] + [[(1, "X"), (2, "XVII"), (3, "VIII"), (0, "XVI")]]
    view = play_view("XIII I", trick=[(0, "XX")], position=1, declarer=1, partner=0, history=late)
    assert played(decide_card(view), view) == "XIII"
    # An announced ulti is lost either way: the pagát stays
    ulti = Announcement(player_position=1, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("XIII I", trick=[(0, "s10")], position=1, declarer=1, partner=0, history=SEVEN_TRICKS,
                     announcements=[ulti])
    assert played(decide_card(view), view) == "XIII"


def test_pagat_goes_when_the_only_hand_with_tarokks_keeps_one_for_the_last_trick():
    # Problem report 20261116-072005: I am the declarer (seat 2) with the ♦J and the pagát. Seats 3 and 0
    # have shown they hold no tarokk, and two are still out: both sit with seat 1, who plays one now
    # and beats the pagát with the other in the last trick.
    history = [
        [(3, "s10"), (0, "sJ"), (1, "II"), (2, "XXI")], [(2, "IV"), (3, "VII"), (0, "XVIII"), (1, "skiz")],
        [(1, "c10"), (2, "cK"), (3, "cJ"), (0, "V")], [(0, "hJ"), (1, "III"), (2, "VI"), (3, "XI")],
        [(3, "sQ"), (0, "XIV"), (1, "XVI"), (2, "XIX")], [(2, "XV"), (3, "dC"), (0, "X"), (1, "VIII")],
        [(2, "XX"), (3, "cC"), (0, "hK"), (1, "IX")],
    ]
    view = play_view("dJ I", position=2, declarer=2, partner=0, history=history)
    view.skart_tarokks = 1  # the XVII lies in seat 1's skart: XIII and XII are in the hands
    d = decide_card(view)
    assert played(d, view) == "I" and d.reason_key == "hint.lead.pagat_drop"
    assert d.reason_params["count"] == 2
    # Were two of the three in a skart, seat 1 would play its last tarokk now: the pagát waits
    view = play_view("dJ I", position=2, declarer=2, partner=0, history=history)
    view.skart_tarokks = 2
    assert played(decide_card(view), view) == "dJ"


def test_pagat_is_led_in_the_second_last_trick_when_more_than_three_tarokks_are_out():
    history = SEVEN_TRICKS[:6] + [[(1, "X"), (2, "sJ"), (3, "sC"), (0, "s9")]]  # XVII, VIII, XX stay out too
    view = play_view("XIII I", position=1, declarer=1, partner=0, history=history)
    d = decide_card(view)
    assert played(d, view) == "I" and d.reason_key == "hint.lead.pagat_drop"
    # Three out: they can all fall on my tarokk lead
    view = play_view("XIII I", position=1, declarer=1, partner=0, history=SEVEN_TRICKS)
    assert played(decide_card(view), view) == "XIII"


def test_defender_keeps_a_tarokk_against_an_announced_ulti():
    ulti = Announcement(player_position=1, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("XV hQ h10", position=0, declarer=0, partner=2, announcements=[ulti])
    d = decide_card(view)
    assert played(d, view) == "h10" and d.reason_key == "hint.lead.keep_tarokk_for_ulti"


def test_saving_the_xxi_comes_before_the_pagat_ulti_rules():
    # My fellow defender plays last: the tarokk lead that lets their XXI home beats keeping it
    ulti = Announcement(player_position=1, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("XV hQ h10", position=0, declarer=1, partner=2, announcements=[ulti])
    d = decide_card(view)
    assert played(d, view) == "XV" and d.reason_key == "hint.lead.partner_last_tarokk"
    # I announced pagát ulti but hold the skíz with the XXI still out: wait for it, do not draw tarokks
    mine = Announcement(player_position=0, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    view = play_view("skiz I XX X IX VIII hQ h10", position=0, declarer=0, announcements=[mine])
    d = decide_card(view)
    assert played(d, view) == "h10" and d.reason_key == "hint.lead.skiz_suit"


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


def test_giver_of_a_taken_invit_discards_cheap_cards():
    # I invited with the XIX and seat 1 took the auction: I will be called, my skart counts against us
    view = discard_view("XXI XIX X IX hK hQ dC dJ sQ s10", 1)
    view.declarer_position = 1
    view.invit = {"by": 0, "card": "XIX"}
    chosen = [c for c in view.hand if c.id in decide_discard(view).payload["card_ids"]]
    assert [(c.suit.value, c.rank) for c in chosen] == [("diamonds", "J")]
    # Somebody else's invit says nothing about me: I discard for the defenders
    view.invit = {"by": 2, "card": "XIX"}
    chosen = [c for c in view.hand if c.id in decide_discard(view).payload["card_ids"]]
    assert [(c.suit.value, c.rank) for c in chosen] == [("diamonds", "C")]


def test_leads_the_suit_a_teammate_is_void_in():
    # Seat 3 (fellow defender) could not follow diamonds earlier
    history = [[(1, "dK"), (2, "dQ"), (3, "II"), (0, "d10")]]
    trull = Announcement(player_position=1, announcement_type=AnnouncementType.TRULL)
    view = play_view("hQ hJ h10 dJ", declarer=1, partner=2, history=history, announcements=[trull])
    assert played(decide_card(view), view) == "dJ"


def test_called_partner_announces_trull_with_a_great_honour_unless_the_declarer_said_ulti():
    """Trull means: our team holds the skíz and the XXI. A declarer without one says pagát ulti."""
    d = decide_announcement(announce_view("skiz XXI X hK hQ hJ h10 dQ dJ", partner=True))
    assert d.payload["announcement_types"] == ["trull"] and d.reason_key == "hint.announce.trull_partner"
    ulti = Announcement(player_position=0, announcement_type=AnnouncementType.PAGAT_ULTIMO)
    for hand in ("skiz X hK hQ hJ h10 dQ dJ d10", "XXI X hK hQ hJ h10 dQ dJ d10"):
        d = decide_announcement(announce_view(hand, partner=True))
        assert d.payload["announcement_types"] == ["trull"] and d.reason_key == "hint.announce.trull_partner_one"
        warned = announce_view(hand, partner=True, made=("pagat_ultimo",))
        warned.announcements = [ulti]
        assert decide_announcement(warned).action == "pass_announcement"


def test_declarer_on_the_pagat_alone_says_ulti_as_information():
    view = announce_view("I X IX VIII hK hQ hJ h10 dQ")
    view.position = view.declarer_position
    d = decide_announcement(view)
    assert d.payload["announcement_types"] == ["pagat_ultimo"] and d.reason_key == "hint.announce.ulti_signal"
    with_honour = announce_view("I XXI IX VIII hK hQ hJ h10 dQ")
    with_honour.position = with_honour.declarer_position
    assert decide_announcement(with_honour).action == "pass_announcement"


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


def test_skiz_expecting_to_be_called_keeps_its_tarokks():
    # Problem report 20261115-201501: seat 3 won the bidding and I hold the XX, so I will be called
    view = discard_view("skiz XX XIX XVI XIV IV I cQ dJ sQ s10", 2)
    view.declarer_position = 3
    d = decide_discard(view)
    chosen = [c for c in view.hand if c.id in d.payload["card_ids"]]
    assert not any(c.is_tarokk() for c in chosen) and d.reason_key == "hint.discard.suits"
    # The giver of a taken invit is called as well
    view = discard_view("skiz XIX XVII XII X VII V hQ dJ sQ", 1)
    view.declarer_position = 1
    view.invit = {"by": 0, "card": "XIX"}
    assert decide_discard(view).reason_key == "hint.discard.suits"
    # The declarer holding skíz and XX is not called by anybody: the hand is weakened as before
    view = discard_view("skiz XX XIX XVI XIV IV I cQ dJ sQ s10", 2)
    view.declarer_position = 0
    assert decide_discard(view).reason_key == "hint.discard.skiz_weaken"


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


def test_enemy_team_kontras_four_kings_with_five_tarokks_above_the_xiii():
    strong = "XIX XVIII XVII XVI XIV hK hQ hJ h10"
    d = decide_announcement(kontra_view(strong, AnnouncementType.FOUR_KINGS, by=1))
    assert d.action == "contra" and d.payload["announcement_type"] == "four_kings"
    assert d.reason_key == "hint.announce.kontra_four_kings_high"
    # Four tarokks above the XIII are not enough
    weak = "XIX XVIII XVII XVI XIII hK hQ hJ h10"
    assert decide_announcement(kontra_view(weak, AnnouncementType.FOUR_KINGS, by=1)).action == "pass_announcement"


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


def test_partner_answers_the_declarers_tarokk_lead_with_the_called_card():
    """Problem report 20261113-152818-da8e4b."""
    hand = "XX VIII IV I dQ dC h10 sC"
    view = play_view(hand, trick=[(0, "V")], position=1, declarer=0, i_am_partner=True)
    d = decide_card(view)
    assert d.reason_key == "hint.follow.show_called" and played(d, view) == "XX"
    # Not when a higher tarokk already lies there, and not on a suit lead
    high = play_view(hand, trick=[(0, "XXI")], position=1, declarer=0, i_am_partner=True)
    assert decide_card(high).reason_key != "hint.follow.show_called"
    suit = play_view(hand, trick=[(0, "dK")], position=1, declarer=0, i_am_partner=True)
    assert decide_card(suit).reason_key != "hint.follow.show_called"
    # Not with a great honour in hand: the XXI catch comes first
    for honour in ("skiz", "XXI"):
        held = play_view(hand.replace("VIII", honour), trick=[(0, "V")], position=1, declarer=0, i_am_partner=True)
        assert decide_card(held).reason_key != "hint.follow.show_called"


def test_declarers_side_leads_a_tarokk_when_it_has_one():
    view = play_view("XVII IX V hQ hJ dC sJ", position=1, declarer=1)
    d = decide_card(view)
    assert d.reason_key == "hint.lead.declarer_tarokk" and played(d, view) == "V"
    # A defender with the same hand does not
    assert decide_card(play_view("XVII IX V hQ hJ dC sJ", position=0, declarer=1)).reason_key != "hint.lead.declarer_tarokk"
    # The XXI stays back while the skíz can catch it
    only_xxi = play_view("XXI hQ hJ dC sJ", position=1, declarer=1)
    assert played(decide_card(only_xxi), only_xxi) != "XXI"


# ---- the route through the decision tree

def test_decision_carries_the_route_through_the_tree():
    from bots.strategy import decide_for_seat
    gs = make_state(["XXI XX X IX hK hQ dC dJ sQ", "skiz hJ", "I cJ", "II cQ"])
    gs.phase = GamePhase.BIDDING
    d = decide_for_seat(gs, 0)
    assert d.reason_key == "hint.bid.xxi_always"
    checks = [(step["check"], step["matched"]) for step in d.route]
    assert checks[0] == ("if not (has_skiz or has_xxi or has_pagat):", False)
    assert ("if has_xxi:", True) in checks
    # Nothing after the rule that decided, except the safety net every bid passes through
    assert [text for text, matched in checks if matched] == ["if has_xxi:"]
    # The route stays on the server: hints sent to a client do not carry it
    assert "route" not in d.to_dict()



# ------------------------------------------- the waiting skíz and who leads next

def test_waiting_skiz_takes_the_lead_from_a_teammate_whose_lead_frees_the_xxi():
    # Report 20261115-162235: declarer on seat 3, partner on 2. Bertike (seat 0) is winning with
    # the XIII; if he leads next, the declarer plays last and the XXI goes home. From my seat
    # (1) the declarer plays before Bertike and cannot know which of us holds the skíz.
    view = play_view("skiz XVI XIV XII I hC sC sJ", trick=[(2, "IV"), (3, "III"), (0, "XIII")],
                     position=1, declarer=3, partner=2,
                     history=[[(3, "h10"), (0, "VI"), (1, "hK"), (2, "VIII")]])
    decision = decide_card(view)
    assert decision.reason_key == "hint.follow.skiz_take_lead"
    assert played(decision, view) == "XIV"


def test_waiting_skiz_keeps_ducking_when_taking_the_lead_frees_the_xxi_just_as_well():
    # Teams sit alternately and I cannot tell which opponent holds the XXI: whoever of us
    # leads, one of them plays last. Nothing is gained, so stay out of the lead.
    view = play_view("skiz XVI XIV XII hC sC sJ", trick=[(3, "IV"), (0, "XIII"), (1, "III")],
                     position=2, declarer=1, partner=3)
    decision = decide_card(view)
    assert decision.reason_key == "hint.follow.skiz_duck_high"
    assert played(decision, view) == "XII"


def test_waiting_skiz_with_the_pagat_knows_the_xxi_is_the_declarers():
    # With skíz and pagát in my hand the bidder's honour is the XXI. Declarer on seat 3 plays
    # last when my teammate (seat 0) leads, but not when I (seat 2) lead: take the lead.
    taking = play_view("skiz XVI XIV XII I sC sJ", trick=[(3, "IV"), (0, "XIII"), (1, "III")],
                       position=2, declarer=3, partner=1)
    assert decide_card(taking).reason_key == "hint.follow.skiz_take_lead"
    # Declarer on seat 1: my teammate's lead keeps the XXI in, mine would let it go. Duck.
    ducking = play_view("skiz XVI XIV XII I sC sJ", trick=[(3, "IV"), (0, "XIII"), (1, "III")],
                        position=2, declarer=1, partner=3)
    assert decide_card(ducking).reason_key == "hint.follow.skiz_duck_high"


def test_waiting_skiz_does_not_take_over_while_others_still_play():
    view = play_view("skiz XVI XIV XII I hC sC sJ", trick=[(3, "III"), (0, "XIII")],
                     position=1, declarer=3, partner=2)
    assert decide_card(view).reason_key == "hint.follow.skiz_duck_high"
