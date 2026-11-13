"""Figures belong to a side, and silent double game counts."""

from game_logic.final_scoring import calculate_final_score
from models.announcement import Announcement, AnnouncementType
from models.bid import Bid, BidType
from tests.test_rule_corrections import cards, make_state

BIG = "hK dK sK skiz XXI I hQ dQ sQ cQ hC dC sC cC hJ dJ sJ cJ XX XIX XVIII XVII XVI XV"


def score(declarer: str, partner: str = "", defender: str = "", announcements=(), history=(), partner_position=2):
    gs = make_state()
    gs.players[0].tricks_won.extend(cards(declarer))
    gs.players[2].tricks_won.extend(cards(partner))
    gs.players[1].tricks_won.extend(cards(defender))
    return calculate_final_score(
        players=gs.players, declarer_position=0, partner_position=partner_position,
        winning_bid=Bid(player_position=0, bid_type=BidType.THREE),
        announcements=list(announcements), trick_history=list(history),
    )


def kinds(result, achieved=True):
    return [(a["type"], a["announced"]) for a in result["announcement_details"] if a["achieved"] is achieved]


def test_partner_announced_four_kings_made_by_both():
    # The screenshot: partner announced, declarer took three kings, partner one
    kings = Announcement(player_position=2, announcement_type=AnnouncementType.FOUR_KINGS, announced=True)
    result = score("hK dK sK", "cK", announcements=[kings])
    assert kinds(result) == [("four_kings", True)]
    assert kinds(result, achieved=False) == []
    assert result["player_scores"] == {0: 50 - 1 + 2, 2: 50 - 1 + 2, 1: 50 + 1 - 2, 3: 50 + 1 - 2}


def test_silent_four_kings_split_between_partners():
    result = score("hK dK", "sK cK")
    assert ("four_kings", False) in kinds(result)


def test_four_kings_fails_when_a_defender_holds_one():
    kings = Announcement(player_position=0, announcement_type=AnnouncementType.FOUR_KINGS, announced=True)
    result = score("hK dK sK", defender="cK", announcements=[kings])
    assert kinds(result, achieved=False) == [("four_kings", True)]
    assert ("four_kings", False) not in kinds(result)


def test_silent_trull_split_between_defenders():
    gs = make_state()
    gs.players[1].tricks_won.extend(cards("skiz XXI"))
    gs.players[3].tricks_won.extend(cards("I"))
    result = calculate_final_score(
        players=gs.players, declarer_position=0, partner_position=2,
        winning_bid=Bid(player_position=0, bid_type=BidType.THREE),
        announcements=[], trick_history=[],
    )
    trull = [a for a in result["announcement_details"] if a["type"] == "trull"]
    assert len(trull) == 1 and trull[0]["team"] == "opponent_team" and trull[0]["achieved"]


def test_silent_double_game_doubles_the_game():
    result = score(BIG, "cK")
    assert result["declarer_team_points"] >= 71
    assert ("double_game", False) in kinds(result)
    assert result["game_multiplier"] == 2
    assert result["final_game_value"] == 2 * result["base_game_value"]
    assert sum(result["player_scores"].values()) == 200


def test_announced_double_game_is_four_times_and_not_also_silent():
    double = Announcement(player_position=2, announcement_type=AnnouncementType.DOUBLE_GAME, announced=True)
    result = score(BIG, "cK", announcements=[double])
    assert result["game_multiplier"] == 4
    assert ("double_game", False) not in kinds(result)


def test_no_double_game_below_71():
    result = score("hK dK sK cK skiz XXI I hQ dQ sQ cQ hC dC sC cC hJ dJ", partner_position=None)
    assert result["declarer_team_points"] < 71
    assert result["game_multiplier"] == 1


def test_bonus_is_shared_by_the_side():
    result = score("hK dK", "sK cK")  # silent four kings, 1 point; defenders win the game
    game = result["final_game_value"]
    assert result["player_scores"][0] == result["player_scores"][2] == 50 - game + 1
    assert result["player_scores"][1] == result["player_scores"][3] == 50 + game - 1


def last_trick(winner, plays):
    trick = {"winner": winner, "cards": [
        {"player_position": pos, "card": {"suit": "tarokk", "rank": rank}} for pos, rank in plays
    ]}
    return [{"winner": 0, "cards": []}] * 8 + [trick]


def test_pagat_ultimo_announced_by_partner_played_by_declarer():
    ulti = Announcement(player_position=2, announcement_type=AnnouncementType.PAGAT_ULTIMO, announced=True)
    result = score("hK", announcements=[ulti], history=last_trick(0, [(0, "I")]))
    assert ("pagat_ultimo", True) in kinds(result)


def test_skiz_on_partners_xxi_is_no_catch():
    history = [{"winner": 0, "cards": [
        {"player_position": 0, "card": {"suit": "tarokk", "rank": "skiz"}},
        {"player_position": 2, "card": {"suit": "tarokk", "rank": "XXI"}},
    ]}]
    assert "xxi_catch" not in [k for k, _ in kinds(score("hK", history=history))]
    history[0]["cards"][1]["player_position"] = 1
    assert ("xxi_catch", False) in kinds(score("hK", history=history))


def test_xxi_catch_from_recorded_trick_format():
    # Same shape the game records: card.to_dict() per play
    skiz, xxi = cards("skiz XXI")
    history = [{"trick_number": 3, "winner": 3, "winner_name": "x", "lead_suit": "tarokk", "cards": [
        {"player_position": 0, "card": xxi.to_dict()},
        {"player_position": 3, "card": skiz.to_dict()},
    ]}]
    result = score("hK", history=history)
    catch = [a for a in result["announcement_details"] if a["type"] == "xxi_catch"]
    assert len(catch) == 1 and catch[0]["team"] == "opponent_team" and catch[0]["points"] == 21
    assert result["player_scores"][0] == result["player_scores"][2]
    assert result["player_scores"][1] == result["player_scores"][3] == 50 + result["final_game_value"] + 21


def test_failed_announced_double_game_and_volat_cost_their_multiple():
    # The reported hand: declarer announced double game, partner volát; the defenders won
    double = Announcement(player_position=0, announcement_type=AnnouncementType.DOUBLE_GAME, announced=True)
    volat = Announcement(player_position=2, announcement_type=AnnouncementType.VOLAT, announced=True)
    result = score("hK", defender="dK", announcements=[double, volat])
    base = result["base_game_value"]
    assert result["winner"] == "opponent_team" and result["final_game_value"] == base
    lost = {a["type"]: a["points"] for a in result["announcement_details"] if not a["achieved"]}
    assert lost == {"double_game": -4 * base, "volat": -6 * base}
    assert result["player_scores"][0] == result["player_scores"][2] == 50 - base - 4 * base - 6 * base
    assert result["player_scores"][1] == result["player_scores"][3] == 50 + base + 4 * base + 6 * base


def test_failed_double_game_is_paid_even_when_the_game_is_won():
    double = Announcement(player_position=0, announcement_type=AnnouncementType.DOUBLE_GAME, announced=True)
    result = score("hK dK sK cK skiz XXI I hQ dQ sQ cQ hC dC sC cC hJ dJ", announcements=[double])
    base = result["base_game_value"]
    assert result["winner"] == "declarer_team" and result["declarer_team_points"] < 71
    bonus = sum(a["points"] for a in result["announcement_details"] if a["type"] not in ("double_game", "volat"))
    assert result["player_scores"][0] == 50 + base - 4 * base + bonus


def test_kontra_doubles_a_failed_double_game():
    double = Announcement(player_position=0, announcement_type=AnnouncementType.DOUBLE_GAME, announced=True, contra=True)
    result = score("hK", defender="dK", announcements=[double])
    lost = [a for a in result["announcement_details"] if a["type"] == "double_game"][0]
    assert lost["points"] == -8 * result["base_game_value"]
