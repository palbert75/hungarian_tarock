"""Position utility functions for counter-clockwise gameplay."""

from typing import Iterator


def next_position(current: int, num_players: int = 4) -> int:
    """
    Get the next position counter-clockwise.

    In Hungarian Tarokk, all actions proceed counter-clockwise around the table.

    Args:
        current: Current position (0-3)
        num_players: Total number of players (default 4)

    Returns:
        Next position counter-clockwise
    """
    return (current + 1) % num_players


def prev_position(current: int, num_players: int = 4) -> int:
    """
    Get the previous position (clockwise).

    Args:
        current: Current position (0-3)
        num_players: Total number of players (default 4)

    Returns:
        Previous position (clockwise)
    """
    return (current - 1) % num_players


def dealer_right(dealer: int, num_players: int = 4) -> int:
    """
    Get the position to the dealer's right (counter-clockwise).

    The player to the dealer's right:
    - Starts the bidding
    - Leads to the first trick

    Args:
        dealer: Dealer's position (0-3)
        num_players: Total number of players (default 4)

    Returns:
        Position to dealer's right
    """
    return next_position(dealer, num_players)


def iter_counter_clockwise(start: int, num_players: int = 4) -> Iterator[int]:
    """
    Iterate through positions counter-clockwise starting from a position.

    Args:
        start: Starting position (0-3)
        num_players: Total number of players (default 4)

    Yields:
        Positions in counter-clockwise order
    """
    for i in range(num_players):
        yield (start + i) % num_players


def distance_counter_clockwise(from_pos: int, to_pos: int, num_players: int = 4) -> int:
    """
    Calculate the counter-clockwise distance between two positions.

    Args:
        from_pos: Starting position
        to_pos: Target position
        num_players: Total number of players (default 4)

    Returns:
        Number of steps counter-clockwise from from_pos to to_pos
    """
    return (to_pos - from_pos) % num_players
