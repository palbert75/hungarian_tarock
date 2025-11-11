"""Calculate final scoring with announcements and payments."""

from typing import List, Dict, Tuple
from models.player import Player
from models.announcement import Announcement, AnnouncementType
from models.bid import Bid
from game_logic.announcement_checker import (
    check_announcement_achieved,
    check_silent_achievements
)


def calculate_team_scores(
    players: List[Player],
    declarer_position: int,
    partner_position: int
) -> Tuple[int, int]:
    """
    Calculate card points for both teams.

    Hungarian Tarokk rules:
    - Declarer's team: Declarer's tricks + Partner's tricks + ONLY Declarer's discards
    - Opponents: Other players' tricks + ALL OTHER discards (including partner's!)

    Args:
        players: All players
        declarer_position: Declarer's position
        partner_position: Partner's position

    Returns:
        Tuple of (declarer_team_points, opponent_team_points)
    """
    declarer_team_points = 0
    opponent_team_points = 0

    declarer = players[declarer_position]
    partner = players[partner_position] if partner_position is not None else None

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


def calculate_final_score(
    players: List[Player],
    declarer_position: int,
    partner_position: int,
    winning_bid: Bid,
    announcements: List[Announcement],
    trick_history: List[dict]
) -> Dict:
    """
    Calculate the complete final score including all bonuses and payments.

    Every player starts with 50 points. Winners receive points, losers pay points.

    Args:
        players: All players
        declarer_position: Declarer's position
        partner_position: Partner's position
        winning_bid: The winning bid
        announcements: All announcements made
        trick_history: Complete history of all tricks

    Returns:
        Dictionary with complete scoring breakdown and payments
    """
    # Calculate card points
    declarer_team_points, opponent_team_points = calculate_team_scores(
        players, declarer_position, partner_position
    )

    # Determine winner
    declarer_won = declarer_team_points >= 48
    winning_team = "declarer_team" if declarer_won else "opponent_team"

    # Check which announcements were achieved
    achieved_announcements = []
    failed_announcements = []

    for announcement in announcements:
        if check_announcement_achieved(
            announcement, players, declarer_position, partner_position,
            trick_history, declarer_team_points, opponent_team_points
        ):
            achieved_announcements.append(announcement)
        else:
            failed_announcements.append(announcement)

    # Check for silent achievements
    silent_achievements = check_silent_achievements(
        players, declarer_position, partner_position, announcements
    )
    achieved_announcements.extend(silent_achievements)

    # Calculate base game value
    base_game_value = winning_bid.game_value

    # Apply double game / volat multipliers
    game_multiplier = 1
    for announcement in achieved_announcements:
        if announcement.announcement_type in [AnnouncementType.DOUBLE_GAME, AnnouncementType.VOLAT]:
            mult = announcement.get_multiplier()
            if mult > game_multiplier:
                game_multiplier = mult

    final_game_value = base_game_value * game_multiplier

    # Initialize payments: everyone starts at 50
    player_scores = {i: 50 for i in range(4)}

    # Calculate base game payments
    # Losing team pays game value to each member of winning team
    if declarer_won:
        # Each opponent pays final_game_value
        for i in range(4):
            if i in [declarer_position, partner_position]:
                # Declarer team: receive payment from each opponent (2 opponents)
                player_scores[i] += final_game_value * 2
            else:
                # Opponents: pay to each declarer team member
                player_scores[i] -= final_game_value
    else:
        # Declarer lost
        for i in range(4):
            if i in [declarer_position, partner_position]:
                # Declarer team: pay to each opponent (2 opponents)
                player_scores[i] -= final_game_value * 2
            else:
                # Opponents: receive from each declarer team member
                player_scores[i] += final_game_value

    # Calculate announcement bonus payments
    announcement_details = []

    for announcement in achieved_announcements:
        player_pos = announcement.player_position
        is_declarer_team = player_pos in [declarer_position, partner_position]
        points = announcement.get_points()

        # Announcement achieved: announcing player's team receives points
        # Each member of opposing team pays the announcing player
        if is_declarer_team:
            # Declarer team member achieved: each opponent pays
            for i in range(4):
                if i not in [declarer_position, partner_position]:
                    player_scores[player_pos] += points
                    player_scores[i] -= points
        else:
            # Opponent achieved: each declarer team member pays
            for i in [declarer_position, partner_position]:
                player_scores[player_pos] += points
                player_scores[i] -= points

        announcement_details.append({
            "type": announcement.announcement_type.value,
            "player_position": player_pos,
            "announced": announcement.announced,
            "points": points,
            "achieved": True,
            "contra": announcement.contra,
            "recontra": announcement.recontra
        })

    # Failed announcements: announcing player's team PAYS the points
    for announcement in failed_announcements:
        player_pos = announcement.player_position
        is_declarer_team = player_pos in [declarer_position, partner_position]
        points = announcement.get_points()

        # Failed announcement: announcing player pays to each opposing team member
        if is_declarer_team:
            # Declarer team failed: they pay each opponent
            for i in range(4):
                if i not in [declarer_position, partner_position]:
                    player_scores[player_pos] -= points
                    player_scores[i] += points
        else:
            # Opponent failed: they pay each declarer team member
            for i in [declarer_position, partner_position]:
                player_scores[player_pos] -= points
                player_scores[i] += points

        announcement_details.append({
            "type": announcement.announcement_type.value,
            "player_position": player_pos,
            "announced": announcement.announced,
            "points": -points,  # Negative to show it's a penalty
            "achieved": False,
            "contra": announcement.contra,
            "recontra": announcement.recontra
        })

    return {
        "declarer_team_points": declarer_team_points,
        "opponent_team_points": opponent_team_points,
        "winner": winning_team,
        "base_game_value": base_game_value,
        "game_multiplier": game_multiplier,
        "final_game_value": final_game_value,
        "player_scores": player_scores,  # Final scores for each player (starting from 50)
        "achieved_announcements": [a.to_dict() for a in achieved_announcements],
        "failed_announcements": [a.to_dict() for a in failed_announcements],
        "announcement_details": announcement_details,
    }
