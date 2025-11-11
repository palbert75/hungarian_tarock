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

      this.socket = io(this.serverUrl, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5,
      })

      // Connection events
      this.socket.on('connect', () => {
        console.log('[Socket] Connected:', this.socket?.id)
        useGameStore.getState().setConnectionStatus('connected')
        useGameStore.getState().setPlayerInfo(this.socket!.id!, playerName)
        resolve()
      })

      this.socket.on('connect_error', (error) => {
        console.error('[Socket] Connection error:', error)
        useGameStore.getState().setConnectionStatus('error')
        useGameStore.getState().addToast({
          type: 'error',
          message: 'Failed to connect to server',
        })
        reject(error)
      })

      this.socket.on('disconnect', (reason) => {
        console.log('[Socket] Disconnected:', reason)
        useGameStore.getState().setConnectionStatus('disconnected')

        if (reason === 'io server disconnect') {
          // Server disconnected us, try to reconnect
          this.socket?.connect()
        }
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

        // Find our position
        const myName = useGameStore.getState().playerName
        const player = data.players.find((p) => p.name === myName)
        if (player) {
          useGameStore.getState().setPlayerPosition(player.position)
        }
      })

      // Game events
      this.socket.on('game_state', (data: GameState) => {
        console.log('[Socket] Game state:', data)
        useGameStore.getState().setGameState(data)
      })

      this.socket.on('game_started', () => {
        console.log('[Socket] Game started')
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
        const playerName = useGameStore
          .getState()
          .gameState?.players[data.player_position]?.name
        useGameStore.getState().addToast({
          type: 'info',
          message: `${playerName} bid: ${data.bid_type}`,
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
        const winnerName = useGameStore
          .getState()
          .gameState?.players[data.winner]?.name
        useGameStore.getState().addToast({
          type: 'success',
          message: `${winnerName} won trick ${data.trick_number}!`,
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

  joinRoom(roomId?: string) {
    const { playerName } = useGameStore.getState()
    this.socket?.emit('join_room', {
      player_name: playerName,
      room_id: roomId || null,
    })
  }

  ready() {
    this.socket?.emit('ready', {})
  }

  placeBid(bidType: string) {
    this.socket?.emit('place_bid', { bid_type: bidType })
  }

  pass() {
    this.socket?.emit('pass', {})
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

  passAnnouncement() {
    this.socket?.emit('pass_announcement', {})
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
