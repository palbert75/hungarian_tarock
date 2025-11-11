"""Check if announcements were achieved using trick history."""

from typing import List, Dict
from models.player import Player
from models.announcement import Announcement, AnnouncementType


def check_trull(player: Player) -> bool:
    """
    Check if player collected all 3 honours (skíz, XXI, pagát).

    Args:
        player: Player to check

    Returns:
        True if player has all 3 honours in tricks_won
    """
    honours = [c for c in player.tricks_won if c.is_honour()]

    # Must have exactly 3 honours, and they must be the specific ones
    if len(honours) != 3:
        return False

    honour_ranks = {c.rank.lower() for c in honours}
    return {'skiz', 'xxi', 'i'} == honour_ranks


def check_four_kings(player: Player) -> bool:
    """
    Check if player collected all 4 kings.

    Args:
        player: Player to check

    Returns:
        True if player has all 4 kings in tricks_won
    """
    kings = [c for c in player.tricks_won if c.is_king()]
    return len(kings) == 4


def check_double_game(team_points: int) -> bool:
    """
    Check if team achieved double game (71+ points).

    Args:
        team_points: Total card points scored by the team

    Returns:
        True if team scored 71+ points
    """
    return team_points >= 71


def check_volat(team_tricks: int) -> bool:
    """
    Check if team won all 9 tricks.

    Args:
        team_tricks: Number of tricks won by the team

    Returns:
        True if team won all 9 tricks
    """
    return team_tricks == 9


def check_pagat_ultimo(trick_history: List[dict], player_position: int) -> bool:
    """
    Check if pagát won the last trick (trick 9) and was played by the specified player.

    Args:
        trick_history: Complete history of all tricks
        player_position: Position of player who announced pagát ultimó

    Returns:
        True if pagát won the last trick for this player
    """
    if len(trick_history) < 9:
        return False

    last_trick = trick_history[8]  # 9th trick (0-indexed)
    winner = last_trick['winner']

    # Check if the player won the last trick
    if winner != player_position:
        return False

    # Check if pagát was the winning card (played by the winner)
    for card_info in last_trick['cards']:
        if card_info['player_position'] == winner:
            card = card_info['card']
            # Pagát is tarokk rank I
            if card['suit'] == 'tarokk' and card['rank'] == 'I':
                return True

    return False


def check_xxi_catch(trick_history: List[dict], player_position: int) -> bool:
    """
    Check if skíz captured opponent's XXI in any trick.

    Args:
        trick_history: Complete history of all tricks
        player_position: Position of player who announced XXI catch

    Returns:
        True if skíz captured XXI
    """
    for trick in trick_history:
        winner = trick['winner']

        # Check if this player won the trick
        if winner != player_position:
            continue

        # Check if skíz was played by winner
        winner_played_skiz = False
        opponent_played_xxi = False

        for card_info in trick['cards']:
            card = card_info['card']
            card_player = card_info['player_position']

            if card_player == player_position:
                # Check if this player played skíz
                if card['suit'] == 'tarokk' and card['rank'].lower() == 'skiz':
                    winner_played_skiz = True
            else:
                # Check if opponent played XXI
                if card['suit'] == 'tarokk' and card['rank'] == 'XXI':
                    opponent_played_xxi = True

        # If skíz captured XXI, this is a catch
        if winner_played_skiz and opponent_played_xxi:
            return True

    return False


def check_announcement_achieved(
    announcement: Announcement,
    players: List[Player],
    declarer_position: int,
    partner_position: int,
    trick_history: List[dict],
    declarer_team_points: int,
    opponent_team_points: int
) -> bool:
    """
    Check if an announcement was actually achieved.

    Args:
        announcement: The announcement to check
        players: All players
        declarer_position: Declarer's position
        partner_position: Partner's position
        trick_history: Complete history of all tricks
        declarer_team_points: Card points scored by declarer's team
        opponent_team_points: Card points scored by opponents

    Returns:
        True if the announcement was achieved
    """
    player = players[announcement.player_position]
    is_declarer_team = player.position in [declarer_position, partner_position]

    if announcement.announcement_type == AnnouncementType.TRULL:
        return check_trull(player)

    elif announcement.announcement_type == AnnouncementType.FOUR_KINGS:
        return check_four_kings(player)

    elif announcement.announcement_type == AnnouncementType.DOUBLE_GAME:
        team_points = declarer_team_points if is_declarer_team else opponent_team_points
        return check_double_game(team_points)

    elif announcement.announcement_type == AnnouncementType.VOLAT:
        # Calculate team tricks
        team_tricks = sum(
            len(p.tricks_won) // 4
            for p in players
            if (p.position in [declarer_position, partner_position]) == is_declarer_team
        )
        return check_volat(team_tricks)

    elif announcement.announcement_type == AnnouncementType.PAGAT_ULTIMO:
        return check_pagat_ultimo(trick_history, announcement.player_position)

    elif announcement.announcement_type == AnnouncementType.XXI_CATCH:
        return check_xxi_catch(trick_history, announcement.player_position)

    return False


def check_silent_achievements(
    players: List[Player],
    declarer_position: int,
    partner_position: int,
    announcements: List[Announcement]
) -> List[Announcement]:
    """
    Check for silently achieved bonuses (not announced but achieved).
    Only checks trull and four kings (silent achievements).

    Args:
        players: All players
        declarer_position: Declarer's position
        partner_position: Partner's position
        announcements: List of announced bonuses

    Returns:
        List of silent achievements as Announcement objects
    """
    silent_bonuses = []
    announced_types_by_player = {
        (a.player_position, a.announcement_type) for a in announcements
    }

    # Check each player for trull and four kings
    for player in players:
        # Check for silent Trull
        if (player.position, AnnouncementType.TRULL) not in announced_types_by_player:
            if check_trull(player):
                silent_bonuses.append(Announcement(
                    player_position=player.position,
                    announcement_type=AnnouncementType.TRULL,
                    announced=False
                ))

        # Check for silent Four Kings
        if (player.position, AnnouncementType.FOUR_KINGS) not in announced_types_by_player:
            if check_four_kings(player):
                silent_bonuses.append(Announcement(
                    player_position=player.position,
                    announcement_type=AnnouncementType.FOUR_KINGS,
                    announced=False
                ))

    return silent_bonuses
