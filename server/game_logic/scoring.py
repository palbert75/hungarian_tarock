"""Scoring logic for Hungarian Tarokk."""

from typing import List, Tuple, Dict, Optional
from models.player import Player
from models.announcement import Announcement, AnnouncementType
from models.bid import Bid


def calculate_player_points(player: Player) -> int:
    """
    Calculate total card points for a player.

    Includes:
    - Points from tricks won
    - Points from discard pile

    Args:
        player: The player

    Returns:
        Total card points
    """
    return player.get_total_points()


def calculate_team_scores(
    players: List[Player],
    declarer_position: int,
    partner_position: int
) -> Tuple[int, int]:
    """
    Calculate scores for both teams.

    Hungarian Tarokk rules:
    - Declarer's team: Declarer's tricks + Partner's tricks + ONLY Declarer's discards
    - Opponents: Other players' tricks + ALL OTHER discards (including partner's!)

    Args:
        players: List of all players
        declarer_position: Position of declarer
        partner_position: Position of partner

    Returns:
        Tuple of (declarer_team_points, opponent_team_points)
    """
    declarer_team_points = 0
    opponent_team_points = 0

    for player in players:
        # Count tricks won
        tricks_points = sum(c.points for c in player.tricks_won)

        if player.position == declarer_position:
            # Declarer: tricks + discards go to declarer team
            discard_points = sum(c.points for c in player.discard_pile)
            declarer_team_points += tricks_points + discard_points
        elif player.position == partner_position:
            # Partner: tricks go to declarer team, but discards go to OPPONENTS!
            declarer_team_points += tricks_points
            discard_points = sum(c.points for c in player.discard_pile)
            opponent_team_points += discard_points
        else:
            # Opponents: tricks + discards go to opponent team
            discard_points = sum(c.points for c in player.discard_pile)
            opponent_team_points += tricks_points + discard_points

    return declarer_team_points, opponent_team_points


def determine_winner(declarer_team_points: int, opponent_team_points: int) -> str:
    """
    Determine which team won.

    Declarer's team needs 48+ points to win (more than half of 94 total).

    Args:
        declarer_team_points: Points scored by declarer's team
        opponent_team_points: Points scored by opponents

    Returns:
        "declarer_team" or "opponent_team"
    """
    if declarer_team_points >= 48:
        return "declarer_team"
    return "opponent_team"


def calculate_game_value(
    base_game_value: int,
    declarer_team_points: int,
    bonuses: List[str] = None
) -> int:
    """
    Calculate the final game value including multipliers.

    Args:
        base_game_value: Base value from bid (three=1, two=2, one=3, solo=4)
        declarer_team_points: Points scored by declarer's team
        bonuses: List of achieved bonuses

    Returns:
        Final game value
    """
    game_value = base_game_value
    bonuses = bonuses or []

    # Double game: 71+ points (doubles game value)
    if declarer_team_points >= 71 and "double_game" in bonuses:
        game_value *= 2

    # Volát: all 9 tricks (triples game value)
    if "volat" in bonuses:
        game_value *= 3

    return game_value


def calculate_payments(
    declarer_position: int,
    partner_position: int,
    game_value: int,
    winner: str,
    num_players: int = 4
) -> Dict[int, int]:
    """
    Calculate payments for all players.

    Winning team receives game_value from each losing player.

    Args:
        declarer_position: Position of declarer
        partner_position: Position of partner
        game_value: Final game value
        winner: "declarer_team" or "opponent_team"
        num_players: Number of players (default 4)

    Returns:
        Dictionary mapping player position to payment (positive = win, negative = loss)
    """
    payments = {}

    declarer_team = {declarer_position, partner_position}
    opponent_team = {i for i in range(num_players) if i not in declarer_team}

    if winner == "declarer_team":
        # Declarer's team wins: each opponent pays game_value
        for pos in declarer_team:
            # Each declarer team member receives game_value from each opponent
            payments[pos] = game_value * len(opponent_team)

        for pos in opponent_team:
            payments[pos] = -game_value

    else:
        # Opponents win: each declarer team member pays game_value to each opponent
        for pos in declarer_team:
            payments[pos] = -game_value * len(opponent_team)

        for pos in opponent_team:
            # Each opponent receives game_value from each declarer team member
            payments[pos] = game_value * len(declarer_team)

    return payments


def calculate_bonus_points(
    players: List[Player],
    declarer_position: int,
    partner_position: int
) -> Dict[str, Tuple[str, int]]:
    """
    Calculate bonus points achieved.

    Bonuses:
    - Trull: All 3 honours (skíz, XXI, pagát) - 1 pt silent / 2 pts announced
    - Four Kings: All 4 Kings - 1 pt silent / 2 pts announced

    Args:
        players: List of all players
        declarer_position: Position of declarer
        partner_position: Position of partner

    Returns:
        Dictionary of bonus_name -> (team, points)
    """
    bonuses = {}

    # Check each player for bonuses
    for player in players:
        team = "declarer_team" if player.position in [declarer_position, partner_position] else "opponent_team"

        # Check for Trull (all 3 honours)
        honours_in_tricks = [c for c in player.tricks_won if c.is_honour()]
        if len(honours_in_tricks) == 3:
            bonuses["trull"] = (team, 1)  # Silent trull (1 point)

        # Check for Four Kings
        kings_in_tricks = [c for c in player.tricks_won if c.is_king()]
        if len(kings_in_tricks) == 4:
            bonuses["four_kings"] = (team, 1)  # Silent four kings (1 point)

    return bonuses


def validate_total_points(declarer_team_points: int, opponent_team_points: int) -> bool:
    """
    Validate that total points add up to 94.

    Args:
        declarer_team_points: Points scored by declarer's team
        opponent_team_points: Points scored by opponents

    Returns:
        True if valid (total = 94)
    """
    return declarer_team_points + opponent_team_points == 94
