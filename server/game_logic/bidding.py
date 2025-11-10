"""Bidding logic for Hungarian Tarokk."""

from typing import List, Optional
from models.bid import Bid, BidType
from models.player import Player
from validation.rules import has_honour


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

        # Check HOLD conditions
        if bid_type == BidType.HOLD:
            player_has_bid = any(
                b.player_position == player.position and b.bid_type not in [BidType.PASS, BidType.HOLD]
                for b in bid_history
            )
            if not player_has_bid:
                return False, "Cannot HOLD - must have already bid in this auction"

            # Must have a bid to hold
            highest_bid = BiddingManager.get_highest_bid(bid_history)
            if highest_bid is None:
                return False, "No bid to hold"

        # Check if bid is higher than current highest (except PASS and HOLD)
        if bid_type not in [BidType.PASS, BidType.HOLD]:
            highest_bid = BiddingManager.get_highest_bid(bid_history)
            new_bid = Bid(player_position=player.position, bid_type=bid_type)

            if not new_bid.is_higher_than(highest_bid):
                return False, "Bid must be higher than current highest bid"

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
        non_pass_bids = [b for b in bid_history if b.bid_type != BidType.PASS]
        if not non_pass_bids:
            return None
        return max(non_pass_bids, key=lambda b: b.game_value)

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
        valid_bids = [BidType.PASS]  # Can always pass

        if not has_honour(player.hand):
            # No honour: can only pass
            return valid_bids

        # Determine which bids are higher than current highest
        highest_bid = BiddingManager.get_highest_bid(bid_history)

        for bid_type in [BidType.THREE, BidType.TWO, BidType.ONE, BidType.SOLO]:
            test_bid = Bid(player_position=player.position, bid_type=bid_type)
            if test_bid.is_higher_than(highest_bid):
                valid_bids.append(bid_type)

        # Check if HOLD is valid
        player_has_bid = any(
            b.player_position == player.position and b.bid_type not in [BidType.PASS, BidType.HOLD]
            for b in bid_history
        )
        if player_has_bid and highest_bid is not None:
            valid_bids.append(BidType.HOLD)

        return valid_bids
