"""Bidding logic for Hungarian Tarokk."""

from typing import List, Optional
from models.bid import Bid, BidType
from models.player import Player
from validation.rules import has_honour
from models.card import TarokkRank
from models.game_state import can_hold, highest_bid_of, invit_card_for, is_yield_turn


def _holds(player: Player, rank: str) -> bool:
    return any(c.is_tarokk() and c.rank == rank for c in player.hand)


def convention_error(player: Player, bid_type: BidType, bid_history: List[Bid]) -> Optional[str]:
    """Why this bid breaks the rules of conventional bidding, or None if it does not."""
    card = invit_card_for(player.position, bid_type, bid_history)
    if card and not _holds(player, card):
        return f"A jump bid here is an invit: you need the {card} for it"
    if bid_type == BidType.PASS and is_yield_turn(player.position, bid_history):
        big = _holds(player, TarokkRank.SKIZ.value) or _holds(player, TarokkRank.XXI.value)
        if not (_holds(player, TarokkRank.XX.value) and big):
            return "Passing here yields the game: you need the XX and the skíz or the XXI for it"
    return None


class BiddingManager:
    """Manages the bidding phase of Hungarian Tarokk."""

    @staticmethod
    def can_player_bid(player: Player, bid_type: BidType, bid_history: List[Bid]) -> tuple[bool, str]:
        """
        Check if a player can make a specific bid.

        Args:
            player: The player attempting to bid
            bid_type: Type of bid
            bid_history: History of bids in this auction

        Returns:
            Tuple of (can_bid, error_message)
        """
        # Check honour requirement for non-PASS/HOLD bids
        if bid_type not in [BidType.PASS, BidType.HOLD]:
            if not has_honour(player.hand):
                return False, "Must have at least one honour (skíz, XXI, or pagát) to bid"

        # A pass is final
        if bid_type != BidType.PASS and any(
            b.player_position == player.position and b.bid_type == BidType.PASS for b in bid_history
        ):
            return False, "Already passed in this auction"

        # Check HOLD conditions
        if bid_type == BidType.HOLD and not can_hold(player.position, bid_history):
            return False, "Cannot HOLD - only a player who has already bid may hold a later, higher bid"

        # Check if bid is higher than current highest (except PASS and HOLD)
        if bid_type not in [BidType.PASS, BidType.HOLD]:
            highest_bid = BiddingManager.get_highest_bid(bid_history)
            new_bid = Bid(player_position=player.position, bid_type=bid_type)

            if not new_bid.is_higher_than(highest_bid):
                return False, "Bid must be higher than current highest bid"

        error = convention_error(player, bid_type, bid_history)
        if error:
            return False, error

        return True, "OK"

    @staticmethod
    def get_highest_bid(bid_history: List[Bid]) -> Optional[Bid]:
        """
        Get the current highest bid (excluding PASS).

        Args:
            bid_history: List of bids

        Returns:
            Highest bid or None if no bids
        """
        return highest_bid_of(bid_history)

    @staticmethod
    def is_auction_complete(bid_history: List[Bid], num_players: int = 4) -> bool:
        """
        Check if the bidding auction is complete.

        Auction ends when:
        1. Someone bids SOLO (highest bid, ends immediately)
        2. All players PASS (no winner, cards thrown in)
        3. After first round, 3 consecutive PASS after a bid

        Args:
            bid_history: List of bids
            num_players: Number of players (default 4)

        Returns:
            True if auction is complete
        """
        if not bid_history:
            return False

        # SOLO ends auction immediately
        if any(b.bid_type == BidType.SOLO for b in bid_history):
            return True

        # All players passed (no winner)
        if len(bid_history) >= num_players and all(b.bid_type == BidType.PASS for b in bid_history):
            return True

        # After first round of bidding, check for 3 consecutive passes
        if len(bid_history) >= num_players:
            # Get last 3 bids
            last_three = bid_history[-(num_players - 1):]
            if len(last_three) == 3 and all(b.bid_type == BidType.PASS for b in last_three):
                # Check if there's at least one non-PASS bid before these passes
                earlier_bids = bid_history[:-(num_players - 1)]
                if any(b.bid_type != BidType.PASS for b in earlier_bids):
                    return True

        return False

    @staticmethod
    def get_declarer_position(bid_history: List[Bid]) -> Optional[int]:
        """
        Determine the declarer from bid history.

        Args:
            bid_history: List of bids

        Returns:
            Position of declarer, or None if all passed
        """
        highest_bid = BiddingManager.get_highest_bid(bid_history)
        if highest_bid:
            return highest_bid.player_position
        return None

    @staticmethod
    def get_valid_bid_types(player: Player, bid_history: List[Bid]) -> List[BidType]:
        """
        Get list of valid bid types for a player.

        Args:
            player: The player
            bid_history: Current bid history

        Returns:
            List of valid bid types
        """
        if not has_honour(player.hand):
            # No honour: can only pass
            return [BidType.PASS]

        candidates = [BidType.PASS, BidType.THREE, BidType.TWO, BidType.ONE, BidType.SOLO, BidType.HOLD]
        return [b for b in candidates if BiddingManager.can_player_bid(player, b, bid_history)[0]]

    @staticmethod
    def invit_bids(player: Player, bid_history: List[Bid]) -> dict:
        """Of the bids this player may make, those that would be an invit: {bid: invited tarokk}."""
        result = {}
        for bid_type in BiddingManager.get_valid_bid_types(player, bid_history):
            card = invit_card_for(player.position, bid_type, bid_history)
            if card:
                result[bid_type.value] = card
        return result
