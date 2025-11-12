"""Test script to verify persistence is working correctly."""

import asyncio
import sqlite3
import json
from persistence.database import GameDatabase
from persistence.persistence_manager import PersistenceManager
from networking.room_manager import RoomManager

async def test_persistence():
    """Test persistence functionality."""

    # Initialize
    db_path = "data/tarokk_game.db"
    persistence = PersistenceManager(db_path)
    room_manager = RoomManager()

    print("=" * 60)
    print("TESTING PERSISTENCE")
    print("=" * 60)

    # Load rooms
    print("\n1. Loading rooms from database...")
    count = await persistence.load_all_rooms(room_manager)
    print(f"   ✓ Loaded {count} room(s)")

    # Check room details
    if count > 0:
        print("\n2. Checking loaded room details...")
        for room_id, room in room_manager.rooms.items():
            print(f"\n   Room ID: {room_id[:8]}...")
            print(f"   Phase: {room.game_state.phase.value}")
            print(f"   Players: {len(room.game_state.players)}")

            for player in room.game_state.players:
                print(f"\n   Player: {player.name} (pos {player.position})")
                print(f"     - Connected: {player.is_connected}")
                print(f"     - Hand size: {len(player.hand)}")
                print(f"     - Tricks won: {len(player.tricks_won)} cards")
                print(f"     - Discard pile: {len(player.discard_pile)} cards")

                # Show first card in hand if any
                if player.hand:
                    card = player.hand[0]
                    print(f"     - First card: {card.rank} of {card.suit.value}")

            print(f"\n   Trick number: {room.game_state.trick_number}")
            print(f"   Current turn: {room.game_state.current_turn}")
            print(f"   Current trick: {len(room.game_state.current_trick)} cards")
            print(f"   Talon: {len(room.game_state.talon)} cards")
            print(f"   Chat messages: {len(room.chat_messages)}")

    # Check database directly
    print("\n3. Checking database directly...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM rooms WHERE is_active=1")
    room_count = cursor.fetchone()[0]
    print(f"   Active rooms in DB: {room_count}")

    cursor.execute("SELECT COUNT(*) FROM players")
    player_count = cursor.fetchone()[0]
    print(f"   Total players in DB: {player_count}")

    cursor.execute("SELECT COUNT(*) FROM game_states")
    state_count = cursor.fetchone()[0]
    print(f"   Game states in DB: {state_count}")

    cursor.execute("SELECT COUNT(*) FROM chat_messages")
    chat_count = cursor.fetchone()[0]
    print(f"   Chat messages in DB: {chat_count}")

    # Check game_data JSON
    cursor.execute("SELECT LENGTH(game_data), phase FROM game_states")
    row = cursor.fetchone()
    if row:
        json_size, phase = row
        print(f"   Game data size: {json_size} bytes")
        print(f"   Game phase: {phase}")

        # Check if player hands are in JSON
        cursor.execute("SELECT game_data FROM game_states")
        game_data_str = cursor.fetchone()[0]
        game_data = json.loads(game_data_str)

        if 'players' in game_data and len(game_data['players']) > 0:
            p0 = game_data['players'][0]
            print(f"\n   Player 0 in JSON:")
            print(f"     - Name: {p0.get('name')}")
            print(f"     - Hand: {len(p0.get('hand', []))} cards")
            print(f"     - Tricks: {len(p0.get('tricks_won', []))} cards")
            print(f"     - Discards: {len(p0.get('discard_pile', []))} cards")

    conn.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    persistence.close()

if __name__ == "__main__":
    asyncio.run(test_persistence())
