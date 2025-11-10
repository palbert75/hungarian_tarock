#!/usr/bin/env python3
"""
Interactive test client for Hungarian Tarokk.

Allows you to control 4 different players and test the game flow.
"""

import sys
import time
from typing import Dict, List, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from client import TarokkClient


def roman_to_int(roman: str) -> int:
    """Convert Roman numeral to integer."""
    roman_values = {
        'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100
    }
    result = 0
    prev_value = 0

    for char in reversed(roman.upper()):
        value = roman_values.get(char, 0)
        if value < prev_value:
            result -= value
        else:
            result += value
        prev_value = value

    return result


def get_tarokk_sort_key(rank: str) -> int:
    """Get sort key for tarokk cards (higher is better, so XXII=22, I=1)."""
    # Handle special names
    if rank.lower() == 'skíz':
        return 22
    if rank.lower() == 'pagát':
        return 1

    # Handle Roman numerals
    try:
        return roman_to_int(rank)
    except:
        return 0


def get_suit_rank_value(rank: str) -> int:
    """Get numeric value for suit card rank (higher is better)."""
    rank_values = {
        'K': 5,  # King
        'Q': 4,  # Queen
        'C': 3,  # Cavalier
        'J': 2,  # Jack
        '10': 1
    }
    return rank_values.get(rank, 0)


def get_suit_order(suit: str) -> int:
    """Get sort order for suits."""
    suit_order = {
        'hearts': 1,
        'diamonds': 2,
        'spades': 3,
        'clubs': 4
    }
    return suit_order.get(suit.lower(), 99)


def sort_hand(hand: List[Dict]) -> List[Dict]:
    """
    Sort hand with tarokk cards first (descending), then suit cards by suit (descending within suit).

    Args:
        hand: List of card dictionaries

    Returns:
        Sorted list of cards
    """
    def card_sort_key(card):
        suit = card.get('suit', '').lower()
        rank = card.get('rank', '')

        if suit == 'tarokk':
            # Tarokk cards come first, sorted in descending order (XXII to I)
            # Negate to reverse order (higher roman numeral first)
            return (0, -get_tarokk_sort_key(rank))
        else:
            # Suit cards come second, grouped by suit, then by rank descending
            return (1, get_suit_order(suit), -get_suit_rank_value(rank))

    return sorted(hand, key=card_sort_key)


class MultiPlayerTest:
    """Interactive test environment for 4 players."""

    def __init__(self, server_url: str = "http://localhost:8000"):
        self.server_url = server_url
        self.console = Console()
        self.clients: Dict[int, TarokkClient] = {}
        self.room_id: Optional[str] = None
        self.current_player: int = 0

        # Track state for each player
        self.your_turn_data: Dict[int, Dict] = {}

    def setup_players(self):
        """Create and connect 4 players."""
        self.console.print("[bold cyan]Setting up 4 players...[/bold cyan]")

        player_names = ["Alice", "Bob", "Charlie", "Diana"]

        for i, name in enumerate(player_names):
            client = TarokkClient(self.server_url, name)

            # Store your_turn data
            def make_handler(player_num):
                def handler(data):
                    self.your_turn_data[player_num] = data
                return handler

            client.on("your_turn", make_handler(i))

            if client.connect():
                self.clients[i] = client
                self.console.print(f"[green]✓ {name} connected[/green]")
            else:
                self.console.print(f"[red]✗ {name} failed to connect[/red]")
                return False

        time.sleep(1)
        return True

    def create_room(self):
        """Create a room with first player and have others join."""
        self.console.print("\n[bold cyan]Creating game room...[/bold cyan]")

        # Player 0 creates room
        self.clients[0].join_room()
        time.sleep(1)

        self.room_id = self.clients[0].room_id
        self.console.print(f"[green]Room created: {self.room_id}[/green]")

        # Other players join
        for i in range(1, 4):
            self.clients[i].join_room(self.room_id)
            time.sleep(0.5)

        time.sleep(1)
        self.console.print("[green]✓ All players joined room[/green]")

    def mark_all_ready(self):
        """Mark all players as ready to start."""
        self.console.print("\n[bold cyan]Marking all players ready...[/bold cyan]")

        for i in range(4):
            self.clients[i].ready()
            time.sleep(0.3)

        self.console.print("[yellow]Waiting for game to start and cards to be dealt...[/yellow]")
        time.sleep(3)

        # Check if hands were dealt
        hands_dealt = sum(1 for i in range(4) if len(self.clients[i].get_hand()) > 0)
        if hands_dealt > 0:
            self.console.print(f"[green]✓ Game started! {hands_dealt}/4 players have cards[/green]")
        else:
            self.console.print("[yellow]⚠ Game started but no hands received yet. Wait a moment...[/yellow]")
            time.sleep(2)

    def show_menu(self):
        """Show main menu."""
        self.console.print("\n[bold cyan]═══ Hungarian Tarokk Test Client ═══[/bold cyan]")
        self.console.print("1. View all players' hands")
        self.console.print("2. View game state")
        self.console.print("3. View talon")
        self.console.print("4. View room state")
        self.console.print("5. Switch active player")
        self.console.print("6. Place bid (current player)")
        self.console.print("7. Discard cards (current player)")
        self.console.print("8. Call partner (current player)")
        self.console.print("9. Play card (current player)")
        self.console.print("10. Auto-play current turn")
        self.console.print("11. View current player's options")
        self.console.print("12. Simulate disconnect/reconnect (current player)")
        self.console.print("0. Quit")

    def view_all_hands(self):
        """Display all players' hands."""
        self.console.print("\n[bold]═══ All Players' Hands ═══[/bold]")
        self.console.print("[dim]Test Mode: Showing each player's hand from their client connection[/dim]\n")

        for i in range(4):
            client = self.clients[i]
            hand = client.get_hand()

            self.console.print(f"\n[bold cyan]{client.player_name} (Position {i}):[/bold cyan]")

            if hand and len(hand) > 0:
                # Sort hand before displaying
                sorted_hand = sort_hand(hand)

                # Display hand as a table
                from rich.table import Table
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="cyan", width=4)
                table.add_column("Card", style="white", width=25)
                table.add_column("Type", style="yellow", width=10)
                table.add_column("Points", style="green", width=8)

                for idx, card in enumerate(sorted_hand):
                    suit = card.get('suit', 'unknown')
                    rank = card.get('rank', '?')
                    card_type = card.get('card_type', 'suit')
                    points = card.get('points', 0)

                    # Format card display
                    if suit == 'tarokk':
                        card_display = f"Tarokk {rank}"
                    else:
                        card_display = f"{rank} of {suit}"

                    # Color code by type
                    type_display = card_type.capitalize()
                    if card_type == 'honour':
                        type_display = f"[bold red]{type_display}[/bold red]"
                    elif card_type == 'king':
                        type_display = f"[bold blue]{type_display}[/bold blue]"

                    table.add_row(
                        str(idx),
                        card_display,
                        type_display,
                        str(points)
                    )

                self.console.print(table)
            else:
                # Check if game has started
                phase = client.game_state.get("phase", "unknown")
                if phase == "waiting" or not client.game_state:
                    self.console.print("[dim]  Game not started yet[/dim]")
                else:
                    self.console.print(f"[yellow]  No cards (phase: {phase})[/yellow]")
                    # Debug: show what we got
                    players = client.game_state.get("players", [])
                    if i < len(players):
                        hand_size = players[i].get("hand_size", 0)
                        self.console.print(f"[dim]  Debug: Server says hand_size={hand_size}, position={client.player_position}[/dim]")

    def view_game_state(self):
        """Display game state."""
        self.console.print("\n[bold]═══ Game State ═══[/bold]")
        self.clients[0].print_game_state()

        # Show all players
        table = Table(title="Players")
        table.add_column("Position", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Hand Size", style="green")
        table.add_column("Points", style="yellow")

        for i in range(4):
            client = self.clients[i]
            gs = client.game_state
            players = gs.get("players", [])
            if i < len(players):
                p = players[i]
                table.add_row(
                    str(i),
                    client.player_name,
                    str(p.get("hand_size", 0)),
                    str(p.get("total_points", 0))
                )

        self.console.print(table)

        # Show bid history
        gs = self.clients[0].game_state
        bid_history = gs.get("bid_history", [])
        if bid_history:
            bid_table = Table(title="Bid History")
            bid_table.add_column("Order", style="cyan", width=6)
            bid_table.add_column("Position", style="magenta", width=8)
            bid_table.add_column("Player", style="yellow", width=12)
            bid_table.add_column("Bid", style="green", width=10)
            bid_table.add_column("Value", style="blue", width=6)

            for idx, bid in enumerate(bid_history):
                player_pos = bid.get("player_position", -1)
                player_name = self.clients[player_pos].player_name if 0 <= player_pos < 4 else "?"
                bid_type = bid.get("bid_type", "unknown")
                game_value = bid.get("game_value", 0)

                # Highlight winning bid
                bid_style = "[bold green]" if bid_type not in ["pass"] else ""
                bid_display = f"{bid_style}{bid_type}{'' if not bid_style else '[/bold green]'}"

                bid_table.add_row(
                    str(idx + 1),
                    str(player_pos),
                    player_name,
                    bid_display,
                    str(game_value)
                )

            self.console.print("\n")
            self.console.print(bid_table)

    def view_talon(self):
        """Display the talon cards."""
        self.console.print("\n[bold]═══ Talon ═══[/bold]")

        # Get talon from game state
        gs = self.clients[0].game_state
        talon = gs.get("talon", [])
        phase = gs.get("phase", "unknown")

        if not talon:
            self.console.print("[yellow]Talon is empty or not available[/yellow]")
            self.console.print(f"[dim]Current phase: {phase}[/dim]")
            return

        # Display talon information
        self.console.print(f"[cyan]Phase: {phase}[/cyan]")
        self.console.print(f"[cyan]Total cards in talon: {len(talon)}[/cyan]\n")

        # Display talon as a table
        table = Table(show_header=True, header_style="bold magenta", title="Talon Cards")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Card", style="white", width=25)
        table.add_column("Type", style="yellow", width=10)
        table.add_column("Points", style="green", width=8)

        for idx, card in enumerate(talon):
            suit = card.get('suit', 'unknown')
            rank = card.get('rank', '?')
            card_type = card.get('card_type', 'suit')
            points = card.get('points', 0)

            # Format card display
            if suit == 'tarokk':
                card_display = f"Tarokk {rank}"
            else:
                card_display = f"{rank} of {suit}"

            # Color code by type
            type_display = card_type.capitalize()
            if card_type == 'honour':
                type_display = f"[bold red]{type_display}[/bold red]"
            elif card_type == 'king':
                type_display = f"[bold blue]{type_display}[/bold blue]"

            table.add_row(
                str(idx),
                card_display,
                type_display,
                str(points)
            )

        self.console.print(table)

        # Show total points in talon
        total_points = sum(card.get('points', 0) for card in talon)
        self.console.print(f"\n[bold green]Total points in talon: {total_points}[/bold green]")

    def view_room_state(self):
        """Display room state with all players."""
        self.console.print("\n[bold]═══ Room State ═══[/bold]")

        # Get room state from first client
        room_state = self.clients[0].room_state

        if not room_state:
            self.console.print("[yellow]No room state available[/yellow]")
            return

        # Display room information
        room_id = room_state.get("room_id", "Unknown")
        is_full = room_state.get("is_full", False)
        game_started = room_state.get("game_started", False)

        self.console.print(f"[cyan]Room ID: {room_id}[/cyan]")
        self.console.print(f"[cyan]Room Full: {'Yes' if is_full else 'No'}[/cyan]")
        self.console.print(f"[cyan]Game Started: {'Yes' if game_started else 'No'}[/cyan]\n")

        # Display players in room
        players = room_state.get("players", [])
        if players:
            table = Table(title=f"Players in Room {room_id}")
            table.add_column("Position", style="cyan", width=10)
            table.add_column("Name", style="magenta", width=15)
            table.add_column("Connected", style="green", width=12)
            table.add_column("Ready", style="yellow", width=10)

            for player in players:
                pos = player.get("position", "?")
                name = player.get("name", "Unknown")
                connected = player.get("is_connected", False)
                ready = player.get("is_ready", False)

                connected_display = "✓ Yes" if connected else "✗ No"
                ready_display = "✓ Yes" if ready else "✗ No"

                # Highlight disconnected players in red
                if not connected:
                    connected_display = f"[red]{connected_display}[/red]"
                else:
                    connected_display = f"[green]{connected_display}[/green]"

                # Highlight ready players in green
                if ready:
                    ready_display = f"[green]{ready_display}[/green]"
                else:
                    ready_display = f"[dim]{ready_display}[/dim]"

                table.add_row(
                    str(pos),
                    name,
                    connected_display,
                    ready_display
                )

            self.console.print(table)
        else:
            self.console.print("[yellow]No players in room[/yellow]")

    def switch_player(self):
        """Switch active player."""
        player_num = Prompt.ask(
            "Select player",
            choices=["0", "1", "2", "3"],
            default=str(self.current_player)
        )
        self.current_player = int(player_num)
        client = self.clients[self.current_player]
        self.console.print(f"[green]Switched to {client.player_name}[/green]")

    def place_bid_interactive(self):
        """Place a bid for current player."""
        client = self.clients[self.current_player]

        # Get valid bids if available
        turn_data = self.your_turn_data.get(self.current_player, {})
        valid_bids = turn_data.get("valid_bids", ["three", "two", "one", "solo", "pass", "hold"])

        self.console.print(f"\n[cyan]Valid bids: {', '.join(valid_bids)}[/cyan]")

        bid = Prompt.ask(
            f"Bid for {client.player_name}",
            choices=valid_bids
        )

        client.place_bid(bid)
        self.console.print(f"[green]✓ Placed bid: {bid}[/green]")
        time.sleep(1)

    def discard_cards_interactive(self):
        """Discard cards for current player."""
        client = self.clients[self.current_player]
        hand = client.get_hand()

        if not hand:
            self.console.print("[yellow]No cards to discard[/yellow]")
            return

        # Sort hand to match display
        sorted_hand = sort_hand(hand)

        # Show hand
        client.print_hand()

        # Calculate how many to discard
        hand_size = len(sorted_hand)
        target_size = 9
        num_to_discard = hand_size - target_size

        if num_to_discard <= 0:
            self.console.print("[yellow]Already at 9 cards[/yellow]")
            return

        self.console.print(f"\n[cyan]Need to discard {num_to_discard} cards[/cyan]")

        # Get card indices
        indices_str = Prompt.ask(f"Enter {num_to_discard} card numbers (comma-separated)")
        indices = [int(x.strip()) for x in indices_str.split(",")]

        if len(indices) != num_to_discard:
            self.console.print(f"[red]Must select exactly {num_to_discard} cards[/red]")
            return

        # Get card IDs from sorted hand (indices match displayed order)
        card_ids = [sorted_hand[i]["id"] for i in indices if i < len(sorted_hand)]

        client.discard_cards(card_ids)
        self.console.print(f"[green]✓ Discarded {len(card_ids)} cards[/green]")
        time.sleep(1)

    def call_partner_interactive(self):
        """Call partner for current player."""
        client = self.clients[self.current_player]

        self.console.print("\n[cyan]Common tarokks: XX, XIX, XVIII, XVII...[/cyan]")
        tarokk = Prompt.ask("Call which tarokk?", default="XX")

        client.call_partner(tarokk)
        self.console.print(f"[green]✓ Called partner: {tarokk}[/green]")
        time.sleep(1)

    def play_card_interactive(self):
        """Play a card for current player."""
        client = self.clients[self.current_player]
        hand = client.get_hand()

        if not hand:
            self.console.print("[yellow]No cards to play[/yellow]")
            return

        # Sort hand to match display
        sorted_hand = sort_hand(hand)

        # Show hand
        client.print_hand()

        # Get valid cards if available
        turn_data = self.your_turn_data.get(self.current_player, {})
        valid_card_ids = turn_data.get("valid_cards", [])

        if valid_card_ids:
            # Calculate valid indices from sorted hand
            valid_indices = [i for i, card in enumerate(sorted_hand) if card["id"] in valid_card_ids]
            self.console.print(f"[cyan]Legal cards: {valid_indices}[/cyan]")

        # Get card index
        card_num = int(Prompt.ask("Play which card? (enter number)"))

        if card_num >= len(sorted_hand):
            self.console.print("[red]Invalid card number[/red]")
            return

        # Get card ID from sorted hand (index matches displayed order)
        card_id = sorted_hand[card_num]["id"]
        client.play_card(card_id)
        self.console.print(f"[green]✓ Played card[/green]")
        time.sleep(1)

    def auto_play_turn(self):
        """Automatically play the current turn."""
        client = self.clients[self.current_player]
        gs = client.game_state
        phase = gs.get("phase")

        self.console.print(f"\n[cyan]Auto-playing for {client.player_name} (Phase: {phase})[/cyan]")

        turn_data = self.your_turn_data.get(self.current_player, {})

        if phase == "bidding":
            valid_bids = turn_data.get("valid_bids", ["pass"])
            # Simple strategy: bid if we have valid non-pass bids, otherwise pass
            bid = valid_bids[0] if valid_bids else "pass"
            if "pass" in valid_bids and len(valid_bids) > 1:
                bid = valid_bids[1]  # Prefer non-pass bid
            client.place_bid(bid)
            self.console.print(f"[green]Auto-bid: {bid}[/green]")

        elif phase == "discarding":
            hand = client.get_hand()
            num_to_discard = len(hand) - 9
            if num_to_discard > 0:
                # Discard lowest point cards that can be discarded
                discardable = [c for c in hand if c.get("card_type") not in ["king", "honour"]]
                discardable.sort(key=lambda x: x.get("points", 0))
                to_discard = discardable[:num_to_discard]
                card_ids = [c["id"] for c in to_discard]
                client.discard_cards(card_ids)
                self.console.print(f"[green]Auto-discard: {len(card_ids)} cards[/green]")

        elif phase == "partner_call":
            client.call_partner("XX")
            self.console.print("[green]Auto-call: XX[/green]")

        elif phase == "playing":
            valid_cards = turn_data.get("valid_cards", [])
            hand = client.get_hand()
            if valid_cards and hand:
                # Play first valid card
                for card in hand:
                    if card["id"] in valid_cards:
                        client.play_card(card["id"])
                        self.console.print(f"[green]Auto-play: {card['rank']} of {card['suit']}[/green]")
                        break

        time.sleep(1)

    def view_current_options(self):
        """View current player's available options."""
        client = self.clients[self.current_player]
        turn_data = self.your_turn_data.get(self.current_player, {})

        self.console.print(f"\n[bold]{client.player_name}'s Options:[/bold]")

        if not turn_data:
            self.console.print("[yellow]No turn data available (not your turn?)[/yellow]")
            return

        actions = turn_data.get("valid_actions", [])
        self.console.print(f"[cyan]Valid actions: {', '.join(actions)}[/cyan]")

        if "valid_bids" in turn_data:
            self.console.print(f"[cyan]Valid bids: {', '.join(turn_data['valid_bids'])}[/cyan]")

        if "valid_cards" in turn_data:
            valid_card_ids = turn_data['valid_cards']
            hand = client.get_hand()
            sorted_hand = sort_hand(hand)
            valid_cards_info = [
                f"{i}: {c['rank']} of {c['suit']}"
                for i, c in enumerate(sorted_hand)
                if c['id'] in valid_card_ids
            ]
            self.console.print(f"[cyan]Valid cards:[/cyan]")
            for info in valid_cards_info:
                self.console.print(f"  {info}")

    def simulate_disconnect_reconnect(self):
        """Simulate connection loss and recovery for current player."""
        client = self.clients[self.current_player]

        self.console.print(f"\n[bold yellow]⚠ Simulating connection loss for {client.player_name}[/bold yellow]")

        # Ask for disconnect duration
        duration_str = Prompt.ask(
            "Disconnect duration (seconds)",
            default="3"
        )

        try:
            duration = float(duration_str)
        except ValueError:
            self.console.print("[red]Invalid duration, using 3 seconds[/red]")
            duration = 3.0

        # Simulate disconnect and reconnect
        success = client.simulate_disconnect_and_reconnect(disconnect_duration=duration)

        if success:
            self.console.print(f"[bold green]✓ {client.player_name} successfully recovered![/bold green]")
            # Give time for game state to sync
            time.sleep(2)
        else:
            self.console.print(f"[bold red]✗ {client.player_name} failed to recover[/bold red]")

    def run(self):
        """Run the interactive test client."""
        self.console.print(Panel.fit(
            "[bold cyan]Hungarian Tarokk Multi-Player Test Client[/bold cyan]\n"
            "Control 4 different players to test the game!",
            border_style="cyan"
        ))

        # Setup
        if not self.setup_players():
            self.console.print("[red]Failed to setup players[/red]")
            return

        self.create_room()

        if Confirm.ask("Mark all players ready and start game?", default=True):
            self.mark_all_ready()

        # Main loop
        while True:
            try:
                self.show_menu()

                client = self.clients[self.current_player]
                self.console.print(f"\n[bold]Active Player: {client.player_name} (Position {self.current_player})[/bold]")

                choice = Prompt.ask("Choose action", default="0")

                if choice == "0":
                    break
                elif choice == "1":
                    self.view_all_hands()
                elif choice == "2":
                    self.view_game_state()
                elif choice == "3":
                    self.view_talon()
                elif choice == "4":
                    self.view_room_state()
                elif choice == "5":
                    self.switch_player()
                elif choice == "6":
                    self.place_bid_interactive()
                elif choice == "7":
                    self.discard_cards_interactive()
                elif choice == "8":
                    self.call_partner_interactive()
                elif choice == "9":
                    self.play_card_interactive()
                elif choice == "10":
                    self.auto_play_turn()
                elif choice == "11":
                    self.view_current_options()
                elif choice == "12":
                    self.simulate_disconnect_reconnect()

            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]Error: {e}[/red]")
                import traceback
                traceback.print_exc()

        # Cleanup
        self.console.print("\n[cyan]Disconnecting players...[/cyan]")
        for client in self.clients.values():
            client.disconnect()

        self.console.print("[green]Goodbye![/green]")


def main():
    """Main entry point."""
    server_url = "http://localhost:8000"

    if len(sys.argv) > 1:
        server_url = sys.argv[1]

    test = MultiPlayerTest(server_url)
    test.run()


if __name__ == "__main__":
    main()
