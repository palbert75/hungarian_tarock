"""Socket.IO client for testing Hungarian Tarokk server."""

import socketio
from typing import Callable, Dict, Any, Optional, List
import threading
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


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


class TarokkClient:
    """
    A client for connecting to the Hungarian Tarokk server.

    Can be used for testing and simulating players.
    """

    def __init__(self, server_url: str = "http://localhost:8000", player_name: str = "Player"):
        self.server_url = server_url
        self.player_name = player_name
        self.sio = socketio.Client()
        self.console = Console()

        # Game state
        self.connected = False
        self.room_id: Optional[str] = None
        self.player_position: Optional[int] = None
        self.game_state: Dict[str, Any] = {}
        self.room_state: Dict[str, Any] = {}

        # Reconnection state
        self.was_ready: bool = False
        self.saved_room_id: Optional[str] = None

        # Event handlers
        self.event_handlers: Dict[str, list[Callable]] = {}

        # Setup default event handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup Socket.IO event handlers."""

        @self.sio.event
        def connect(*args):
            self.connected = True
            self.log(f"[green]✓ Connected as {self.player_name}[/green]")

        @self.sio.event
        def disconnect(*args):
            self.connected = False
            self.log(f"[red]✗ Disconnected[/red]")

        @self.sio.event
        def room_state(data):
            self.room_state = data
            self.room_id = data.get("room_id")
            self.saved_room_id = self.room_id  # Save for reconnection

            # Find our position
            for player in data.get("players", []):
                if player.get("name") == self.player_name:
                    self.player_position = player.get("position")
                    self.was_ready = player.get("is_ready", False)

            self._trigger_handlers("room_state", data)

        @self.sio.event
        def game_state(data):
            self.game_state = data
            self._trigger_handlers("game_state", data)

        @self.sio.event
        def game_started(data):
            self.log("[bold green]🎮 Game Started![/bold green]")
            self._trigger_handlers("game_started", data)

        @self.sio.event
        def your_turn(data):
            self.log("[bold yellow]⏰ Your Turn![/bold yellow]")
            self._trigger_handlers("your_turn", data)

        @self.sio.event
        def bid_placed(data):
            player_pos = data.get("player_position")
            bid_type = data.get("bid_type")
            self.log(f"[cyan]Player {player_pos} bid: {bid_type}[/cyan]")
            self._trigger_handlers("bid_placed", data)

        @self.sio.event
        def talon_distributed(data):
            you_received = data.get("you_received")
            hand_size = data.get("your_hand_size")
            self.log(f"[magenta]📦 Received {you_received} cards from talon (hand: {hand_size})[/magenta]")
            self._trigger_handlers("talon_distributed", data)

        @self.sio.event
        def player_discarded(data):
            player_pos = data.get("player_position")
            num_cards = data.get("num_cards")
            self.log(f"[cyan]Player {player_pos} discarded {num_cards} cards[/cyan]")
            self._trigger_handlers("player_discarded", data)

        @self.sio.event
        def partner_called(data):
            called_card = data.get("called_card")
            self.log(f"[bold magenta]🤝 Partner called: {called_card}[/bold magenta]")
            self._trigger_handlers("partner_called", data)

        @self.sio.event
        def partner_revealed(data):
            partner_pos = data.get("partner_position")
            self.log(f"[bold magenta]👥 Partner revealed: Position {partner_pos}[/bold magenta]")
            self._trigger_handlers("partner_revealed", data)

        @self.sio.event
        def announcement_made(data):
            player_pos = data.get("player_position")
            announcement_type = data.get("announcement_type")
            announced = data.get("announced", True)
            status = "announced" if announced else "silent"
            self.log(f"[bold yellow]📢 Player {player_pos} made announcement: {announcement_type} ({status})[/bold yellow]")
            self._trigger_handlers("announcement_made", data)

        @self.sio.event
        def pass_announcement(data):
            player_pos = data.get("player_position")
            self.log(f"[dim]Player {player_pos} passed on announcements[/dim]")
            self._trigger_handlers("pass_announcement", data)

        @self.sio.event
        def announcements_complete(data):
            self.log(f"[bold green]✓ Announcement phase complete[/bold green]")
            self._trigger_handlers("announcements_complete", data)

        @self.sio.event
        def card_played(data):
            player_pos = data.get("player_position")
            card = data.get("card", {})
            card_str = f"{card.get('rank')} of {card.get('suit')}"
            self.log(f"[cyan]🃏 Player {player_pos} played: {card_str}[/cyan]")
            self._trigger_handlers("card_played", data)

        @self.sio.event
        def trick_complete(data):
            winner = data.get("winner")
            trick_num = data.get("trick_number")
            self.log(f"[bold green]✓ Trick {trick_num} won by Player {winner}[/bold green]")
            self._trigger_handlers("trick_complete", data)

        @self.sio.event
        def game_over(data):
            winner = data.get("winner")
            declarer_points = data.get("declarer_team_points")
            opponent_points = data.get("opponent_team_points")
            self.log(f"[bold yellow]🏆 Game Over! Winner: {winner}[/bold yellow]")
            self.log(f"[yellow]Declarer team: {declarer_points} pts, Opponents: {opponent_points} pts[/yellow]")
            self._trigger_handlers("game_over", data)

        @self.sio.event
        def error(data):
            msg = data.get("data", {}).get("message", "Unknown error")
            self.log(f"[bold red]❌ Error: {msg}[/bold red]")
            self._trigger_handlers("error", data)

    def on(self, event: str, handler: Callable):
        """Register a custom event handler."""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)

    def _trigger_handlers(self, event: str, data: Any):
        """Trigger all handlers for an event."""
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    handler(data)
                except Exception as e:
                    self.log(f"[red]Handler error: {e}[/red]")

    def log(self, message: str):
        """Log a message with player name prefix."""
        self.console.print(f"[{self.player_name}] {message}")

    def connect(self):
        """Connect to the server."""
        try:
            self.sio.connect(self.server_url)
            return True
        except Exception as e:
            self.log(f"[red]Connection failed: {e}[/red]")
            return False

    def disconnect(self):
        """Disconnect from the server."""
        if self.connected:
            self.sio.disconnect()

    def reconnect(self, max_retries: int = 3, retry_delay: float = 2.0) -> bool:
        """
        Reconnect to the server and rejoin the previous room.

        Args:
            max_retries: Maximum number of reconnection attempts
            retry_delay: Delay between retry attempts in seconds

        Returns:
            True if reconnection successful, False otherwise
        """
        if self.connected:
            self.log("[yellow]Already connected[/yellow]")
            return True

        if not self.saved_room_id:
            self.log("[red]Cannot reconnect: No saved room ID[/red]")
            return False

        self.log(f"[cyan]Attempting to reconnect to room {self.saved_room_id}...[/cyan]")

        for attempt in range(1, max_retries + 1):
            self.log(f"[cyan]Reconnection attempt {attempt}/{max_retries}...[/cyan]")

            try:
                # Reconnect to server
                self.sio.connect(self.server_url)
                time.sleep(1)  # Wait for connection to stabilize

                if self.connected:
                    self.log("[green]✓ Reconnected to server[/green]")

                    # Rejoin the same room
                    self.log(f"[cyan]Rejoining room {self.saved_room_id}...[/cyan]")
                    self.join_room(self.saved_room_id)
                    time.sleep(1)  # Wait for room_state response

                    if self.room_id == self.saved_room_id:
                        self.log(f"[green]✓ Successfully rejoined room {self.room_id}[/green]")

                        # If we were ready before, mark as ready again
                        if self.was_ready:
                            self.log("[cyan]Marking as ready...[/cyan]")
                            self.ready()
                            time.sleep(0.5)

                        return True
                    else:
                        self.log("[yellow]⚠ Room ID mismatch, retrying...[/yellow]")
                        self.disconnect()
                        time.sleep(retry_delay)
                else:
                    self.log("[yellow]⚠ Connection failed, retrying...[/yellow]")
                    time.sleep(retry_delay)

            except Exception as e:
                self.log(f"[red]Reconnection attempt {attempt} failed: {e}[/red]")
                if attempt < max_retries:
                    self.log(f"[cyan]Waiting {retry_delay}s before retry...[/cyan]")
                    time.sleep(retry_delay)

        self.log("[red]✗ Failed to reconnect after all attempts[/red]")
        return False

    def simulate_disconnect_and_reconnect(self, disconnect_duration: float = 3.0) -> bool:
        """
        Simulate a connection loss and automatic recovery.

        Args:
            disconnect_duration: How long to stay disconnected (seconds)

        Returns:
            True if reconnection successful, False otherwise
        """
        self.log("[bold yellow]⚠ Simulating connection loss...[/bold yellow]")

        # Store current state
        original_room = self.saved_room_id

        # Disconnect
        self.disconnect()
        self.log(f"[red]✗ Disconnected. Waiting {disconnect_duration}s...[/red]")
        time.sleep(disconnect_duration)

        # Attempt reconnection
        self.log("[cyan]🔄 Initiating automatic reconnection...[/cyan]")
        success = self.reconnect()

        if success:
            self.log("[bold green]✓ Connection recovered successfully![/bold green]")
            self.log(f"[green]Back in room: {self.room_id}, Position: {self.player_position}[/green]")
        else:
            self.log("[bold red]✗ Failed to recover connection[/bold red]")

        return success

    def join_room(self, room_id: Optional[str] = None):
        """Join or create a room."""
        self.sio.emit("join_room", {
            "room_id": room_id,
            "player_name": self.player_name
        })
        time.sleep(0.5)  # Wait for room_state response

    def ready(self):
        """Mark player as ready."""
        self.sio.emit("ready", {})

    def place_bid(self, bid_type: str):
        """Place a bid."""
        self.sio.emit("place_bid", {"bid_type": bid_type})

    def discard_cards(self, card_ids: list[str]):
        """Discard cards."""
        self.sio.emit("discard_cards", {"card_ids": card_ids})

    def call_partner(self, tarokk_rank: str):
        """Call partner."""
        self.sio.emit("call_partner", {"tarokk_rank": tarokk_rank})

    def make_announcement(self, announcement_type: str, announced: bool = True):
        """Make an announcement."""
        self.sio.emit("make_announcement", {
            "announcement_type": announcement_type,
            "announced": announced
        })

    def pass_announcement(self):
        """Pass on making announcements."""
        self.sio.emit("pass_announcement", {})

    def play_card(self, card_id: str):
        """Play a card."""
        self.sio.emit("play_card", {"card_id": card_id})

    def get_hand(self) -> list[Dict[str, Any]]:
        """Get current hand cards."""
        # Hand is in players array, find our position
        players = self.game_state.get("players", [])
        if self.player_position is not None and self.player_position < len(players):
            return players[self.player_position].get("hand", [])
        return []

    def get_valid_bids(self) -> list[str]:
        """Get valid bids from last your_turn message."""
        # This would need to be stored from your_turn event
        return []

    def get_valid_cards(self) -> list[str]:
        """Get valid card IDs from last your_turn message."""
        # This would need to be stored from your_turn event
        return []

    def print_hand(self):
        """Print current hand in a nice format."""
        hand = self.get_hand()
        if not hand:
            self.console.print("[yellow]No cards in hand[/yellow]")
            return

        # Sort hand before displaying
        sorted_hand = sort_hand(hand)

        table = Table(title=f"{self.player_name}'s Hand")
        table.add_column("#", style="cyan")
        table.add_column("Card", style="magenta")
        table.add_column("Points", style="green")
        table.add_column("ID", style="dim")

        for i, card in enumerate(sorted_hand):
            card_str = f"{card.get('rank')} of {card.get('suit')}"
            table.add_row(
                str(i),
                card_str,
                str(card.get('points', 0)),
                card.get('id', '')[:8]
            )

        self.console.print(table)

    def print_game_state(self):
        """Print current game state."""
        if not self.game_state:
            self.console.print("[yellow]No game state available[/yellow]")
            return

        panel_content = f"""
[bold]Phase:[/bold] {self.game_state.get('phase', 'N/A')}
[bold]Your Position:[/bold] {self.player_position if self.player_position is not None else 'N/A'}
[bold]Current Turn:[/bold] {self.game_state.get('current_turn', 'N/A')}
[bold]Dealer:[/bold] {self.game_state.get('dealer_position', 'N/A')}
[bold]Declarer:[/bold] {self.game_state.get('declarer_position', 'N/A')}
[bold]Trick:[/bold] {self.game_state.get('trick_number', 0)}
        """

        panel = Panel(panel_content, title="Game State", border_style="blue")
        self.console.print(panel)

    def wait_for_event(self, event: str, timeout: float = 10.0) -> bool:
        """Wait for a specific event to occur."""
        event_occurred = threading.Event()

        def handler(data):
            event_occurred.set()

        self.on(event, handler)
        return event_occurred.wait(timeout)
