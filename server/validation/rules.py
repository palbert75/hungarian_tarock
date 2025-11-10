"""Game rules validation for Hungarian Tarokk."""

from typing import List, Tuple
from models.card import Card, Suit


def get_legal_cards(hand: List[Card], lead_suit: Suit, is_first_card: bool = False) -> List[Card]:
    """
    Get list of legal cards a player can play.

    Rules:
    1. If leading (first card of trick): Can play any card
    2. If following:
       a. Must follow suit if able
       b. If void in lead suit: MUST play tarokk if able
       c. If void in lead suit AND no tarokk: Can play any card

    Args:
        hand: Player's current hand
        lead_suit: The suit that was led (or None if leading)
        is_first_card: True if this is the first card of the trick

    Returns:
        List of legal cards that can be played
    """
    if is_first_card:
        # Leading: can play any card
        return hand

    # Following: must follow suit
    cards_of_lead_suit = [c for c in hand if c.suit == lead_suit]

    if cards_of_lead_suit:
        # Have cards of lead suit: must play one
        return cards_of_lead_suit

    # Void in lead suit: must play tarokk if able
    tarokks = [c for c in hand if c.is_tarokk()]

    if tarokks:
        # Have tarokks: must play one
        return tarokks

    # Void in lead suit AND no tarokks: can play any card
    return hand


def validate_play(card: Card, hand: List[Card], lead_suit: Suit, is_first_card: bool = False) -> Tuple[bool, str]:
    """
    Validate if a card play is legal.

    Args:
        card: Card to play
        hand: Player's current hand
        lead_suit: The suit that was led
        is_first_card: True if this is the first card of the trick

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if card is in hand
    if card not in hand:
        return False, "Card not in hand"

    legal_cards = get_legal_cards(hand, lead_suit, is_first_card)

    if card not in legal_cards:
        # Determine reason for illegality
        if not is_first_card:
            has_lead_suit = any(c.suit == lead_suit for c in hand)
            if has_lead_suit:
                return False, f"Must follow suit: {lead_suit.value}"

            has_tarokk = any(c.is_tarokk() for c in hand)
            if has_tarokk and not card.is_tarokk():
                return False, "Must play tarokk when void in lead suit"

        return False, "Illegal card play"

    return True, "OK"


def validate_discard(cards: List[Card]) -> Tuple[bool, str]:
    """
    Validate if cards can be legally discarded.

    Rules:
    - Cannot discard Kings
    - Cannot discard Honours (skíz, XXI, pagát)

    Args:
        cards: Cards to discard

    Returns:
        Tuple of (is_valid, error_message)
    """
    for card in cards:
        if card.is_king():
            return False, f"Cannot discard Kings: {card}"

        if card.is_honour():
            return False, f"Cannot discard Honours: {card}"

    return True, "OK"


def count_tarokks_in_discard(cards: List[Card]) -> int:
    """
    Count the number of tarokk cards in a discard.

    Players must announce how many tarokks they discard.

    Args:
        cards: Discarded cards

    Returns:
        Number of tarokk cards
    """
    return sum(1 for c in cards if c.is_tarokk())


def can_annul_hand(hand: List[Card]) -> Tuple[bool, str]:
    """
    Check if a player can annul their hand.

    Hand can be annulled if:
    - All four Kings
    - Singleton XXI (only one tarokk, and it's XXI)
    - Singleton pagát (only one tarokk, and it's pagát)
    - No tarokks at all
    - Only XXI + pagát (with restrictions)

    Args:
        hand: Player's hand

    Returns:
        Tuple of (can_annul, reason)
    """
    kings = [c for c in hand if c.is_king()]
    if len(kings) == 4:
        return True, "All four Kings"

    tarokks = [c for c in hand if c.is_tarokk()]

    if len(tarokks) == 0:
        return True, "No tarokks"

    if len(tarokks) == 1:
        tarokk_rank = tarokks[0].rank
        if tarokk_rank == "XXI":
            return True, "Singleton XXI"
        if tarokk_rank == "I":  # pagát
            return True, "Singleton pagát"

    if len(tarokks) == 2:
        ranks = {t.rank for t in tarokks}
        if ranks == {"XXI", "I"}:
            return True, "Only XXI and pagát"

    return False, "Hand cannot be annulled"


def has_honour(hand: List[Card]) -> bool:
    """
    Check if hand contains at least one honour card.

    Honours are: skíz, XXI, or pagát (I)
    Required to place a bid.

    Args:
        hand: Player's hand

    Returns:
        True if hand has at least one honour
    """
    return any(c.is_honour() for c in hand)


def has_trull(hand: List[Card]) -> bool:
    """
    Check if hand contains all three honours (trull).

    Trull = skíz + XXI + pagát

    Args:
        hand: Player's hand

    Returns:
        True if hand has all three honours
    """
    honour_ranks = {c.rank for c in hand if c.is_honour()}
    return {"skiz", "XXI", "I"} <= honour_ranks


def has_four_kings(hand: List[Card]) -> bool:
    """
    Check if hand contains all four Kings.

    Args:
        hand: Player's hand

    Returns:
        True if hand has all four Kings
    """
    return len([c for c in hand if c.is_king()]) == 4
