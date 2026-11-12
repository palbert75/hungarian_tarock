"""Check if announcements were achieved using trick history."""

from typing import List, Dict, Optional, Set
from models.player import Player
from models.announcement import Announcement, AnnouncementType


def team_positions(
    position: int,
    declarer_position: int,
    partner_position: Optional[int],
    num_players: int = 4
) -> Set[int]:
    """Positions of everyone on the same side as `position`."""
    declarer_side = {declarer_position}
    if partner_position is not None:
        declarer_side.add(partner_position)
    if position in declarer_side:
        return declarer_side
    return {i for i in range(num_players) if i not in declarer_side}


def team_cards(players: List[Player], positions: Set[int]) -> list:
    """All cards a side captured in tricks."""
    return [c for p in players if p.position in positions for c in p.tricks_won]


def check_trull(cards: list) -> bool:
    """True if these captured cards hold all three honours (skíz, XXI, pagát)."""
    return {c.rank.lower() for c in cards if c.is_honour()} == {'skiz', 'xxi', 'i'}


def check_four_kings(cards: list) -> bool:
    """True if these captured cards hold all four kings."""
    return len([c for c in cards if c.is_king()]) == 4


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


def _is_tarokk(card: dict, rank: str) -> bool:
    return card['suit'] == 'tarokk' and card['rank'].lower() == rank


def pagat_ultimo_winner(trick_history: List[dict]) -> Optional[int]:
    """Position of the player whose pagát won the last trick, or None."""
    if len(trick_history) < 9:
        return None
    last_trick = trick_history[8]
    winner = last_trick['winner']
    for card_info in last_trick['cards']:
        if card_info['player_position'] == winner and _is_tarokk(card_info['card'], 'i'):
            return winner
    return None


def check_pagat_ultimo(trick_history: List[dict], team: Set[int]) -> bool:
    """True if a member of `team` won the last trick with the pagát."""
    return pagat_ultimo_winner(trick_history) in team


def xxi_catcher(trick_history: List[dict], declarer_side: Set[int]) -> Optional[int]:
    """
    Position of the player whose skíz captured the other side's XXI, or None.
    A skíz that falls on a teammate's XXI is not a catch.
    """
    for trick in trick_history:
        skiz_by = xxi_by = None
        for card_info in trick['cards']:
            if _is_tarokk(card_info['card'], 'skiz'):
                skiz_by = card_info['player_position']
            elif _is_tarokk(card_info['card'], 'xxi'):
                xxi_by = card_info['player_position']
        if skiz_by is not None and xxi_by is not None:
            if (skiz_by in declarer_side) != (xxi_by in declarer_side):
                return skiz_by
            return None
    return None


def check_xxi_catch(trick_history: List[dict], team: Set[int], declarer_side: Set[int]) -> bool:
    """True if a member of `team` caught the other side's XXI with the skíz."""
    return xxi_catcher(trick_history, declarer_side) in team


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
    team = team_positions(
        announcement.player_position, declarer_position, partner_position, len(players)
    )
    declarer_side = team_positions(
        declarer_position, declarer_position, partner_position, len(players)
    )
    is_declarer_team = announcement.player_position in declarer_side
    kind = announcement.announcement_type

    # Every figure belongs to the side, not to the player who announced it.
    if kind == AnnouncementType.TRULL:
        return check_trull(team_cards(players, team))

    if kind == AnnouncementType.FOUR_KINGS:
        return check_four_kings(team_cards(players, team))

    if kind == AnnouncementType.DOUBLE_GAME:
        return check_double_game(declarer_team_points if is_declarer_team else opponent_team_points)

    if kind == AnnouncementType.VOLAT:
        return check_volat(len(team_cards(players, team)) // 4)

    if kind == AnnouncementType.PAGAT_ULTIMO:
        return check_pagat_ultimo(trick_history, team)

    if kind == AnnouncementType.XXI_CATCH:
        return check_xxi_catch(trick_history, team, declarer_side)

    return False


def check_silent_achievements(
    players: List[Player],
    declarer_position: int,
    partner_position: Optional[int],
    announcements: List[Announcement],
    trick_history: Optional[List[dict]] = None,
    declarer_team_points: int = 0,
    opponent_team_points: int = 0
) -> List[Announcement]:
    """
    Figures a side made without announcing them.

    Judged per side. A side that announced a figure gets no silent one of the
    same kind, whether the announced one was made or lost. The silent figure
    is booked on the declarer (declarer's side) or on the first defender.

    Returns:
        List of silent achievements as Announcement objects (announced=False)
    """
    trick_history = trick_history or []
    declarer_side = team_positions(
        declarer_position, declarer_position, partner_position, len(players)
    )
    defenders = {p.position for p in players} - declarer_side
    silent_bonuses: List[Announcement] = []

    for team, points in (
        (declarer_side, declarer_team_points),
        (defenders, opponent_team_points),
    ):
        if not team:
            continue
        holder = declarer_position if team is declarer_side else min(team)
        announced = {
            a.announcement_type for a in announcements if a.player_position in team
        }
        cards = team_cards(players, team)

        def add(kind: AnnouncementType, position: int = holder) -> None:
            if kind not in announced:
                silent_bonuses.append(Announcement(
                    player_position=position, announcement_type=kind, announced=False
                ))

        if check_trull(cards):
            add(AnnouncementType.TRULL)
        if check_four_kings(cards):
            add(AnnouncementType.FOUR_KINGS)
        if check_volat(len(cards) // 4):
            add(AnnouncementType.VOLAT)
        elif check_double_game(points):
            add(AnnouncementType.DOUBLE_GAME)
        ulti_by = pagat_ultimo_winner(trick_history)
        if ulti_by in team:
            add(AnnouncementType.PAGAT_ULTIMO, ulti_by)
        caught_by = xxi_catcher(trick_history, declarer_side)
        if caught_by in team:
            add(AnnouncementType.XXI_CATCH, caught_by)

    return silent_bonuses
