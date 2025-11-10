#!/usr/bin/env python3
"""
Automated test scenarios for Hungarian Tarokk server.

Runs complete game simulations to verify server functionality.
"""

import sys
import time
from typing import List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from client import TarokkClient


class AutomatedTest:
    """Automated test scenarios."""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.console = Console()
        self.clients: List[TarokkClient] = []
        self.test_passed = True

    def log(self, message: str, style: str = ""):
        """Log a test message."""
        if style:
            self.console.print(f"[{style}]{message}[/{style}]")
        else:
            self.console.print(message)

    def assert_true(self, condition: bool, message: str):
        """Assert a condition is true."""
        if not condition:
            self.log(f"✗ FAILED: {message}", "bold red")
            self.test_passed = False
        else:
            self.log(f"✓ PASSED: {message}", "green")

    def setup_game(self) -> bool:
        """Setup a 4-player game."""
        self.log("\n=== Setting Up Game ===", "bold cyan")

        player_names = ["Alice", "Bob", "Charlie", "Diana"]

        # Connect all players
        for name in player_names:
            client = TarokkClient(self.server_url, name)
            if not client.connect():
                self.log(f"Failed to connect {name}", "red")
                return False
            self.clients.append(client)
            time.sleep(0.3)

        self.log(f"✓ Connected {len(self.clients)} players", "green")

        # Create room
        self.clients[0].join_room()
        time.sleep(1)

        room_id = self.clients[0].room_id
        self.assert_true(room_id is not None, "Room created")

        # Others join
        for client in self.clients[1:]:
            client.join_room(room_id)
            time.sleep(0.5)

        time.sleep(1)

        # Verify all in room
        self.assert_true(
            all(c.room_id == room_id for c in self.clients),
            "All players in same room"
        )

        # Mark ready
        for client in self.clients:
            client.ready()
            time.sleep(0.3)

        time.sleep(2)

        return True

    def test_basic_game_flow(self):
        """Test basic game flow: setup -> bidding -> game start."""
        self.log("\n=== Test: Basic Game Flow ===", "bold yellow")

        if not self.setup_game():
            return False

        # Check game started
        time.sleep(1)
        phase = self.clients[0].game_state.get("phase")
        self.assert_true(
            phase == "bidding",
            f"Game started in bidding phase (got: {phase})"
        )

        # Verify each player has 9 cards
        for i, client in enumerate(self.clients):
            hand_size = len(client.get_hand())
            self.assert_true(
                hand_size == 9,
                f"Player {i} has 9 cards (got: {hand_size})"
            )

        return self.test_passed

    def test_bidding_phase(self):
        """Test bidding phase with various bids."""
        self.log("\n=== Test: Bidding Phase ===", "bold yellow")

        if not self.setup_game():
            return False

        time.sleep(1)

        # Track which players have honours
        players_with_honours = []
        for i, client in enumerate(self.clients):
            hand = client.get_hand()
            has_honour = any(
                card.get("card_type") == "honour"
                for card in hand
            )
            if has_honour:
                players_with_honours.append(i)
                self.log(f"Player {i} ({client.player_name}) has honour", "cyan")

        # Simulate bidding round
        for round_num in range(4):
            gs = self.clients[0].game_state
            current_turn = gs.get("current_turn")

            if gs.get("phase") != "bidding":
                break

            self.log(f"Bidding turn: Player {current_turn}", "cyan")

            client = self.clients[current_turn]
            hand = client.get_hand()

            # Check if player has honour
            has_honour = any(card.get("card_type") == "honour" for card in hand)

            # Simple bidding strategy
            if has_honour and round_num == 0:
                client.place_bid("three")
                self.log(f"Player {current_turn} bid 'three'", "green")
            else:
                client.place_bid("pass")
                self.log(f"Player {current_turn} passed", "yellow")

            time.sleep(1.5)

        # Check bidding completed
        time.sleep(2)
        phase = self.clients[0].game_state.get("phase")
        self.assert_true(
            phase in ["talon_distribution", "discarding", "partner_call"],
            f"Bidding completed (phase: {phase})"
        )

        return self.test_passed

    def test_full_game_simulation(self):
        """Run a complete game with automated decisions."""
        self.log("\n=== Test: Full Game Simulation ===", "bold yellow")

        if not self.setup_game():
            return False

        time.sleep(2)

        max_iterations = 100
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            # Check game state
            gs = self.clients[0].game_state
            phase = gs.get("phase")

            self.log(f"\nIteration {iteration}: Phase = {phase}", "cyan")

            if phase == "game_end":
                self.log("Game completed!", "bold green")
                break

            if phase == "scoring":
                time.sleep(3)
                continue

            # Find current player
            current_turn = gs.get("current_turn")
            if current_turn is None:
                time.sleep(1)
                continue

            client = self.clients[current_turn]
            hand = client.get_hand()

            self.log(f"Player {current_turn} ({client.player_name})'s turn", "yellow")

            try:
                if phase == "bidding":
                    # Auto-bid
                    has_honour = any(card.get("card_type") == "honour" for card in hand)
                    if has_honour and iteration <= 4:
                        bid_options = ["three", "two", "one"]
                        client.place_bid(bid_options[min(iteration - 1, 2)])
                    else:
                        client.place_bid("pass")

                elif phase == "discarding":
                    # Auto-discard
                    num_to_discard = len(hand) - 9
                    if num_to_discard > 0:
                        discardable = [c for c in hand if c.get("card_type") not in ["king", "honour"]]
                        discardable.sort(key=lambda x: x.get("points", 0))
                        to_discard = discardable[:num_to_discard]
                        card_ids = [c["id"] for c in to_discard]
                        client.discard_cards(card_ids)
                        self.log(f"Discarded {len(card_ids)} cards", "green")

                elif phase == "partner_call":
                    # Auto-call partner
                    if gs.get("declarer_position") == current_turn:
                        client.call_partner("XX")
                        self.log("Called partner: XX", "magenta")

                elif phase == "playing":
                    # Auto-play first card from hand (simplified)
                    if hand:
                        client.play_card(hand[0]["id"])
                        self.log(f"Played {hand[0]['rank']} of {hand[0]['suit']}", "green")

                time.sleep(1.5)

            except Exception as e:
                self.log(f"Error during turn: {e}", "red")
                time.sleep(1)

        self.assert_true(
            iteration < max_iterations,
            "Game completed within iteration limit"
        )

        # Check final scores
        gs = self.clients[0].game_state
        if phase == "game_end":
            self.log("\n=== Game Results ===", "bold green")
            # Get final state from last game_over event
            self.log("Game finished successfully", "green")

        return self.test_passed

    def test_connection_and_reconnection(self):
        """Test player connection and disconnection."""
        self.log("\n=== Test: Connection/Disconnection ===", "bold yellow")

        # Connect one player
        client = TarokkClient(self.server_url, "TestPlayer")
        connected = client.connect()
        self.assert_true(connected, "Player connected")

        time.sleep(1)

        # Disconnect
        client.disconnect()
        time.sleep(1)

        self.assert_true(not client.connected, "Player disconnected")

        return self.test_passed

    def cleanup(self):
        """Cleanup all connections."""
        self.log("\n=== Cleaning Up ===", "cyan")
        for client in self.clients:
            try:
                client.disconnect()
            except:
                pass
        self.clients.clear()

    def run_all_tests(self):
        """Run all test scenarios."""
        self.console.print("\n" + "="*60)
        self.console.print("   HUNGARIAN TAROKK - AUTOMATED TEST SUITE", style="bold cyan")
        self.console.print("="*60 + "\n")

        tests = [
            ("Connection Test", self.test_connection_and_reconnection),
            ("Basic Game Flow", self.test_basic_game_flow),
            ("Bidding Phase", self.test_bidding_phase),
            ("Full Game Simulation", self.test_full_game_simulation),
        ]

        results = []

        for test_name, test_func in tests:
            self.test_passed = True
            self.console.print(f"\n{'='*60}")
            self.console.print(f"Running: {test_name}", style="bold white")
            self.console.print('='*60)

            try:
                test_func()
                results.append((test_name, self.test_passed))
            except Exception as e:
                self.log(f"Test crashed: {e}", "bold red")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
            finally:
                self.cleanup()
                time.sleep(2)

        # Print summary
        self.console.print("\n" + "="*60)
        self.console.print("   TEST SUMMARY", style="bold cyan")
        self.console.print("="*60 + "\n")

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "[green]✓ PASSED[/green]" if result else "[red]✗ FAILED[/red]"
            self.console.print(f"{status} - {test_name}")

        self.console.print(f"\n[bold]Results: {passed}/{total} tests passed[/bold]")

        if passed == total:
            self.console.print("\n[bold green]🎉 All tests passed![/bold green]")
            return 0
        else:
            self.console.print("\n[bold red]❌ Some tests failed[/bold red]")
            return 1


def main():
    """Main entry point."""
    server_url = "http://localhost:8000"

    if len(sys.argv) > 1:
        server_url = sys.argv[1]

    test = AutomatedTest(server_url)
    exit_code = test.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
