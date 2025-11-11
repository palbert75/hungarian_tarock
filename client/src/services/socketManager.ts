import { io, Socket } from 'socket.io-client'
import { useGameStore } from '@/store/gameStore'
import type { GameState, RoomState, YourTurnData } from '@/types'

class SocketManager {
  private socket: Socket | null = null
  private serverUrl: string

  constructor() {
    this.serverUrl = import.meta.env.VITE_SERVER_URL || 'http://localhost:8000'
  }

  connect(playerName: string): Promise<void> {
    return new Promise((resolve, reject) => {
      useGameStore.getState().setConnectionStatus('connecting')

      console.log('=== Socket.IO Connection Attempt ===')
      console.log('[Socket] Server URL:', this.serverUrl)
      console.log('[Socket] Player Name:', playerName)
      console.log('[Socket] Timestamp:', new Date().toISOString())

      // Check if we have a stored player ID (for reconnection)
      const storedPlayerId = useGameStore.getState().playerId
      if (storedPlayerId) {
        console.log('[Socket] Found stored player ID:', storedPlayerId)
      }

      this.socket = io(this.serverUrl, {
        transports: ['websocket', 'polling'],
        upgrade: true,
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5,
        withCredentials: false,
        autoConnect: true,
      })

      console.log('[Socket] Socket.IO client created')
      console.log('[Socket] Client version:', (io as any).version || 'unknown')

      // Detailed connection lifecycle events
      this.socket.io.on('open', () => {
        console.log('[Socket.io.Engine] ✓ Engine opened (underlying connection established)')
      })

      this.socket.io.on('close', (reason) => {
        console.log('[Socket.io.Engine] ✗ Engine closed:', reason)
      })

      this.socket.io.on('error', (error) => {
        console.error('[Socket.io.Engine] Engine error:', error)
      })

      this.socket.io.on('packet', (packet) => {
        console.log('[Socket.io.Engine] Packet received:', packet.type, packet.data)
      })

      this.socket.io.on('packetCreate', (packet) => {
        console.log('[Socket.io.Engine] Packet created (sending):', packet.type, packet.data)
      })

      // Connection events
      this.socket.on('connect', () => {
        console.log('=== Socket.IO Connected Successfully ===')
        console.log('[Socket] ✓ Socket ID:', this.socket?.id)
        console.log('[Socket] Transport:', this.socket?.io?.engine?.transport?.name)
        console.log('[Socket] Connected at:', new Date().toISOString())
        useGameStore.getState().setConnectionStatus('connected')

        // Store the player name immediately
        // We'll get the actual player ID from the server when we receive room_state after joining a room
        const currentPlayerId = useGameStore.getState().playerId
        const currentPlayerName = useGameStore.getState().playerName

        if (currentPlayerId) {
          console.log('[Socket] Have stored player ID for reconnection:', currentPlayerId)
          // Reconnection case - keep both ID and name
          useGameStore.getState().setPlayerInfo(currentPlayerId, playerName)
        } else {
          // First time connection - store name (ID will come from server)
          console.log('[Socket] Storing player name:', playerName)
          useGameStore.getState().setPlayerInfo('', playerName)
        }

        resolve()
      })

      this.socket.on('connect_error', (error) => {
        console.error('=== Socket.IO Connection Error ===')
        console.error('[Socket] Error object:', error)
        console.error('[Socket] Error message:', error.message)
        console.error('[Socket] Error type:', (error as any).type)
        console.error('[Socket] Error description:', (error as any).description)
        console.error('[Socket] Error context:', (error as any).context)
        console.error('[Socket] Full error:', JSON.stringify(error, null, 2))
        useGameStore.getState().setConnectionStatus('error')
        useGameStore.getState().addToast({
          type: 'error',
          message: `Connection failed: ${error.message}`,
        })
        reject(error)
      })

      this.socket.on('disconnect', (reason) => {
        console.log('=== Socket.IO Disconnected ===')
        console.log('[Socket] Reason:', reason)
        console.log('[Socket] Disconnected at:', new Date().toISOString())
        useGameStore.getState().setConnectionStatus('disconnected')

        if (reason === 'io server disconnect') {
          console.log('[Socket] Server initiated disconnect, attempting reconnect...')
          this.socket?.connect()
        }
      })

      this.socket.on('error', (error) => {
        console.error('[Socket] Socket error event:', error)
      })

      this.socket.on('reconnect_attempt', (attemptNumber) => {
        console.log('[Socket] Reconnection attempt #', attemptNumber)
      })

      this.socket.on('reconnect_error', (error) => {
        console.error('[Socket] Reconnection error:', error)
      })

      this.socket.on('reconnect_failed', () => {
        console.error('[Socket] Reconnection failed after all attempts')
      })

      this.socket.on('reconnect', (attemptNumber) => {
        console.log('[Socket] Reconnected after', attemptNumber, 'attempts')
        useGameStore.getState().setConnectionStatus('connected')
        useGameStore.getState().addToast({
          type: 'success',
          message: 'Reconnected to server',
        })
      })

      this.socket.on('reconnect_attempt', () => {
        useGameStore.getState().setConnectionStatus('reconnecting')
      })

      // Room events
      this.socket.on('room_state', (data: RoomState) => {
        console.log('[Socket] Room state:', data)
        useGameStore.getState().setRoomState(data)

        // Find our player info and update store
        const myName = useGameStore.getState().playerName
        const player = data.players.find((p) => p.name === myName)
        if (player) {
          // Update position
          useGameStore.getState().setPlayerPosition(player.position)

          // Update player ID with server's ID (important for reconnection)
          const currentPlayerId = useGameStore.getState().playerId
          if (currentPlayerId !== player.id) {
            console.log('[Socket] Updating player ID from server:', player.id)
            useGameStore.getState().setPlayerInfo(player.id, myName)
          }
        }
      })

      this.socket.on('rooms_list', (data: { rooms: any[] }) => {
        console.log('[Socket] Rooms list:', data)
        useGameStore.getState().setAvailableRooms(data.rooms)
      })

      // Game events
      this.socket.on('game_state', (data: GameState | { message: string }) => {
        console.log('[Socket] Game state received:', data)

        // Check if it's a message (all players passed)
        if ('message' in data && !('phase' in data)) {
          console.log('[Socket] Message:', data.message)
          useGameStore.getState().addToast({
            type: 'warning',
            message: data.message,
            duration: 4000,
          })
          // Clear selected cards
          useGameStore.getState().clearSelectedCards()
          return
        }

        const gameState = data as GameState
        console.log('[Socket] My position:', useGameStore.getState().playerPosition)
        const myPos = useGameStore.getState().playerPosition
        if (myPos !== null && gameState.players[myPos]) {
          console.log('[Socket] My hand:', gameState.players[myPos].hand)
          console.log('[Socket] Hand size:', gameState.players[myPos].hand?.length || 0)
        }

        // Clear selected cards when new hand is dealt
        const currentPhase = useGameStore.getState().gameState?.phase
        if (currentPhase !== gameState.phase && gameState.phase === 'dealing') {
          useGameStore.getState().clearSelectedCards()
        }

        // Show toast when transitioning from dealing to bidding (new hand dealt)
        if (currentPhase === 'dealing' && gameState.phase === 'bidding') {
          useGameStore.getState().addToast({
            type: 'success',
            message: 'New hand dealt! Bidding begins.',
            duration: 2000,
          })
        }

        useGameStore.getState().setGameState(gameState)
      })

      this.socket.on('game_started', () => {
        console.log('[Socket] *** GAME STARTED ***')

        // Update room state to mark game as started
        const currentRoomState = useGameStore.getState().roomState
        if (currentRoomState) {
          useGameStore.getState().setRoomState({
            ...currentRoomState,
            game_started: true,
          })
          console.log('[Socket] Updated roomState.game_started = true')
        }

        useGameStore.getState().addToast({
          type: 'success',
          message: 'Game started! Good luck!',
        })
      })

      this.socket.on('your_turn', (data: YourTurnData) => {
        console.log('[Socket] Your turn:', data)
        useGameStore.getState().setYourTurnData(data)
        useGameStore.getState().addToast({
          type: 'info',
          message: "It's your turn!",
          duration: 2000,
        })
      })

      // Bidding events
      this.socket.on('bid_placed', (data) => {
        console.log('[Socket] Bid placed:', data)
        const gameState = useGameStore.getState().gameState
        const playerName = gameState?.players[data.player_position]?.name || 'Player'
        const bidType = data.bid_type || 'pass'

        // Format bid display
        const bidDisplay = bidType === 'pass' ? 'Pass' :
                          bidType === 'three' ? 'Three' :
                          bidType === 'two' ? 'Two' :
                          bidType === 'one' ? 'One' :
                          bidType === 'solo' ? 'Solo' :
                          bidType === 'hold' ? 'Hold' : bidType

        useGameStore.getState().addToast({
          type: 'info',
          message: `${playerName} bid: ${bidDisplay}`,
          duration: 2000,
        })
      })

      // Talon events
      this.socket.on('talon_distributed', (data) => {
        console.log('[Socket] Talon distributed:', data)
        useGameStore.getState().addToast({
          type: 'info',
          message: `You received ${data.you_received} cards from talon`,
          duration: 2000,
        })
      })

      // Discard events
      this.socket.on('player_discarded', (data) => {
        console.log('[Socket] Player discarded:', data)
      })

      // Partner events
      this.socket.on('partner_called', (data) => {
        console.log('[Socket] Partner called:', data)
        useGameStore.getState().addToast({
          type: 'info',
          message: `Partner called: ${data.called_card}`,
        })
      })

      this.socket.on('partner_revealed', (data) => {
        console.log('[Socket] Partner revealed:', data)
        const partnerName = useGameStore
          .getState()
          .gameState?.players[data.partner_position]?.name
        useGameStore.getState().addToast({
          type: 'success',
          message: `Partner revealed: ${partnerName}!`,
        })
      })

      // Announcement events
      this.socket.on('announcement_made', (data) => {
        console.log('[Socket] Announcement made:', data)
        const playerName = useGameStore
          .getState()
          .gameState?.players[data.player_position]?.name
        const status = data.announced ? 'announced' : 'silent'
        useGameStore.getState().addToast({
          type: 'info',
          message: `${playerName}: ${data.announcement_type} (${status})`,
        })
      })

      this.socket.on('contra_made', (data) => {
        console.log('[Socket] Contra made:', data)
        const playerName = useGameStore
          .getState()
          .gameState?.players[data.player_position]?.name
        useGameStore.getState().addToast({
          type: 'warning',
          message: `${playerName} contra'd ${data.announcement_type}!`,
        })
      })

      this.socket.on('recontra_made', (data) => {
        console.log('[Socket] Recontra made:', data)
        const playerName = useGameStore
          .getState()
          .gameState?.players[data.player_position]?.name
        useGameStore.getState().addToast({
          type: 'warning',
          message: `${playerName} recontra'd ${data.announcement_type}!`,
        })
      })

      this.socket.on('announcements_complete', () => {
        console.log('[Socket] Announcements complete')
        useGameStore.getState().addToast({
          type: 'success',
          message: 'Announcements complete! Starting tricks...',
        })
      })

      // Trick events
      this.socket.on('card_played', (data) => {
        console.log('[Socket] Card played:', data)
      })

      this.socket.on('trick_started', (data) => {
        console.log('[Socket] Trick started:', data)
      })

      this.socket.on('trick_complete', (data) => {
        console.log('[Socket] Trick complete:', data)
        const gameState = useGameStore.getState().gameState

        // Safely get winner name
        let winnerName = 'Unknown Player'
        if (data.winner !== undefined && data.winner !== null && gameState?.players) {
          const winner = gameState.players[data.winner]
          winnerName = winner && winner.name ? winner.name : `Player ${data.winner + 1}`
        }

        // Safely get trick number
        const trickNumber = data.trick_number !== undefined && data.trick_number !== null
          ? data.trick_number
          : '?'

        useGameStore.getState().addToast({
          type: 'success',
          message: `${winnerName} won trick ${trickNumber}!`,
        })
      })

      // Game over
      this.socket.on('game_over', (data) => {
        console.log('[Socket] Game over:', data)
        useGameStore.getState().addToast({
          type: 'success',
          message: `Game over! Winner: ${data.winner}`,
        })
      })

      // Error handling
      this.socket.on('error', (data) => {
        console.error('[Socket] Error:', data)
        useGameStore.getState().addToast({
          type: 'error',
          message: data.data?.message || 'An error occurred',
        })
      })
    })
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  // Emit methods

  listRooms() {
    console.log('[Socket] Requesting room list')
    this.socket?.emit('list_rooms', {})
  }

  joinRoom(roomId?: string) {
    const { playerName, playerId } = useGameStore.getState()
    this.socket?.emit('join_room', {
      player_name: playerName,
      player_id: playerId,
      room_id: roomId || null,
    })
  }

  // Attempt to reconnect to previous game session
  reconnectToGame(): boolean {
    const { playerId, playerName, roomState } = useGameStore.getState()

    console.log('[Socket] Attempting reconnection...', {
      playerId,
      playerName,
      roomId: roomState?.room_id,
    })

    // Check if we have enough info to reconnect
    if (!playerId || !playerName || !roomState?.room_id) {
      console.log('[Socket] Not enough data for reconnection')
      return false
    }

    // Try to rejoin the room
    console.log('[Socket] Reconnecting to room:', roomState.room_id)
    this.joinRoom(roomState.room_id)
    return true
  }

  ready() {
    this.socket?.emit('ready', {})
  }

  placeBid(bidType: string) {
    console.log('[Socket] Placing bid:', bidType)
    this.socket?.emit('place_bid', { bid_type: bidType })
  }

  pass() {
    console.log('[Socket] Passing (bidding)')
    this.socket?.emit('place_bid', { bid_type: 'pass' })
  }

  discardCards(cardIds: string[]) {
    useGameStore.getState().clearSelectedCards()
    this.socket?.emit('discard_cards', { card_ids: cardIds })
  }

  callPartner(tarokkRank: string) {
    this.socket?.emit('call_partner', { tarokk_rank: tarokkRank })
  }

  makeAnnouncement(announcementType: string, announced: boolean) {
    this.socket?.emit('make_announcement', {
      announcement_type: announcementType,
      announced,
    })
  }

  makeAnnouncements(announcementTypes: string[], announced: boolean) {
    this.socket?.emit('make_announcement', {
      announcement_types: announcementTypes,
      announced,
    })
  }

  passAnnouncement() {
    this.socket?.emit('pass_announcement', {})
  }

  contraAnnouncement(announcementType: string) {
    this.socket?.emit('contra_announcement', {
      announcement_type: announcementType,
    })
  }

  recontraAnnouncement(announcementType: string) {
    this.socket?.emit('recontra_announcement', {
      announcement_type: announcementType,
    })
  }

  playCard(cardId: string) {
    useGameStore.getState().clearSelectedCards()
    this.socket?.emit('play_card', { card_id: cardId })
  }

  leaveRoom() {
    this.socket?.emit('leave_room', {})
    useGameStore.getState().setRoomState(null)
    useGameStore.getState().setGameState(null)
  }
}

// Singleton instance
export const socketManager = new SocketManager()
