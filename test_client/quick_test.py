#!/usr/bin/env python3
"""
Quick test script - rapidly test basic server functionality.

Usage:
    python quick_test.py              # Test local server
    python quick_test.py <server_url> # Test specific server
"""

import sys
import time
from rich.console import Console
from client import TarokkClient


def quick_test(server_url: str = "http://localhost:8000"):
    """Quick test of server functionality."""
    console = Console()

    console.print("\n[bold cyan]🎮 Hungarian Tarokk - Quick Test[/bold cyan]\n")
    console.print(f"Server: {server_url}\n")

    # Test 1: Connection
    console.print("[yellow]Test 1: Connection...[/yellow]")
    client = TarokkClient(server_url, "QuickTest")

    if not client.connect():
        console.print("[red]✗ Connection failed[/red]")
        return False

    console.print("[green]✓ Connected successfully[/green]\n")
    time.sleep(1)

    # Test 2: Create room
    console.print("[yellow]Test 2: Creating room...[/yellow]")
    client.join_room()
    time.sleep(1)

    if not client.room_id:
        console.print("[red]✗ Room creation failed[/red]")
        return False

    console.print(f"[green]✓ Room created: {client.room_id}[/green]\n")

    # Test 3: Room state
    console.print("[yellow]Test 3: Room state...[/yellow]")

    if client.room_state:
        console.print(f"[green]✓ Room state received[/green]")
        console.print(f"  Players: {len(client.room_state.get('players', []))}/4")
        console.print(f"  Room full: {client.room_state.get('is_full', False)}")
    else:
        console.print("[red]✗ No room state[/red]")

    console.print()

    # Cleanup
    console.print("[yellow]Cleaning up...[/yellow]")
    client.disconnect()
    time.sleep(1)

    console.print("\n[bold green]✓ Quick test completed successfully![/bold green]\n")
    return True


def main():
    """Main entry point."""
    server_url = "http://localhost:8000"

    if len(sys.argv) > 1:
        server_url = sys.argv[1]

    try:
        success = quick_test(server_url)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
