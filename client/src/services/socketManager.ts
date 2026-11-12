import { io, Socket } from 'socket.io-client'
import i18n from '@/i18n'
import { useGameStore } from '@/store/gameStore'
import { playSound } from '@/utils/sound'
import { tarokkName } from '@/utils/cardNames'
import type { BotSpeed, GameOverData, GameState, RoomState, TrickCard, YourTurnData } from '@/types'

/** Server messages come either bare or wrapped as { type, data }. */
const unwrap = <T = any>(payload: any): T =>
  payload && typeof payload === 'object' && 'data' in payload && 'type' in payload ? (payload.data as T) : (payload as T)

const store = () => useGameStore.getState()
const t = i18n.t.bind(i18n)

const toast = (type: 'success' | 'error' | 'info' | 'warning', message: string, duration?: number) =>
  store().addToast({ type, message, duration })

/** How long a finished trick stays on the table before it is collected (ms). */
export const TRICK_SHOW_MS = 2200

class SocketManager {
  private socket: Socket | null = null
  private serverUrl: string
  private trickTimer: ReturnType<typeof setTimeout> | null = null

  constructor() {
    this.serverUrl = import.meta.env.VITE_SERVER_URL || 'https://tarokk.onbased.cloud/'
  }

  isStarted(): boolean {
    return this.socket !== null
  }

  /** Open the connection. It keeps retrying on its own for as long as the app is open. */
  connect(): void {
    if (this.socket) return
    store().setConnectionStatus('connecting')

    this.socket = io(this.serverUrl, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
      withCredentials: false,
    })
    const socket = this.socket

    socket.on('connect', () => {
      const wasReconnecting = store().connectionStatus === 'reconnecting'
      store().setConnectionStatus('connected')
      if (wasReconnecting) toast('success', t('toast.reconnected'))

      // Come back to our seat, or follow an invite link
      const { roomId, pendingRoomId } = store()
      if (roomId) {
        this.joinRoom(roomId)
      } else if (pendingRoomId) {
        store().setPendingRoomId(null)
        this.joinRoom(pendingRoomId)
      } else {
        this.listRooms()
      }
    })

    socket.on('connect_error', () => {
      store().setConnectionStatus(store().connectionStatus === 'connecting' ? 'connecting' : 'reconnecting')
    })

    socket.on('disconnect', (reason) => {
      store().setConnectionStatus('reconnecting')
      if (reason === 'io server disconnect') socket.connect()
    })

    // ---- room -------------------------------------------------------------

    socket.on('joined', (data: { room_id: string; player_id: string }) => {
      store().setSeat(data.player_id, data.room_id)
      if (store().quickBots) {
        // "Play against bots": fill the table and start
        store().setQuickBots(false)
        socket.emit('fill_bots', {})
        socket.emit('ready', {})
      }
    })

    socket.on('room_state', (data: RoomState) => {
      const current = store().roomState?.room_id
      if (current && current !== data.room_id) store().clearChatMessages()
      store().setRoomState(data)
    })

    socket.on('rooms_list', (data: { rooms: RoomState[] }) => {
      store().setAvailableRooms(data.rooms || [])
    })

    socket.on('player_connection', (data: { player_name: string; connected: boolean; bot_controlled?: boolean }) => {
      if (data.connected) {
        toast('success', t('toast.playerBack', { name: data.player_name }), 4000)
      } else if (data.bot_controlled) {
        toast('info', t('toast.playerReplaced', { name: data.player_name }), 4000)
      } else {
        toast('warning', t('toast.playerDropped', { name: data.player_name }), 4000)
      }
    })

    // ---- game -------------------------------------------------------------

    socket.on('game_state', (data: GameState | { message: string; code?: string }) => {
      if (!('phase' in data)) {
        if (data.code === 'ALL_PASSED') toast('warning', t('toast.allPassed'), 3500)
        store().clearSelectedCards()
        return
      }
      const previous = store().gameState
      if (previous && previous.game_id !== data.game_id) store().clearSelectedCards()
      // "Your turn" data belongs to one moment; drop it when the turn has moved on
      if (previous && (previous.current_turn !== data.current_turn || previous.phase !== data.phase)) {
        store().setYourTurnData(null)
        store().clearSelectedCards()
      }
      store().setGameState(data)
    })

    socket.on('game_started', () => {
      store().setGameOverData(null)
      store().setFinishedTrick(null)
      store().setYourTurnData(null)
      store().clearSelectedCards()
    })

    socket.on('your_turn', (data: YourTurnData) => {
      store().setYourTurnData(data)
      playSound('turn')
    })

    socket.on('talon_distributed', (payload) => {
      const data = unwrap<{ you_received: number }>(payload)
      if (data.you_received > 0) toast('info', t('toast.talonReceived', { count: data.you_received }), 2500)
    })

    socket.on('player_discarded', (payload) => {
      const data = unwrap<{ player_position: number; tarokks_discarded: number }>(payload)
      if (data.tarokks_discarded > 0) {
        toast('info', t('toast.tarokksDiscarded', {
          name: this.nameAt(data.player_position),
          count: data.tarokks_discarded,
        }), 4000)
      }
    })

    socket.on('partner_called', (payload) => {
      const data = unwrap<{ called_card: string }>(payload)
      toast('info', t('toast.partnerCalled', { card: tarokkName(data.called_card, t) }), 3500)
    })

    socket.on('partner_revealed', (payload) => {
      const data = unwrap<{ partner_position: number }>(payload)
      toast('success', t('toast.partnerRevealed', { name: this.nameAt(Number(data.partner_position)) }), 3500)
    })

    socket.on('contra_made', (payload) => {
      const data = unwrap<{ player_position: number; announcement_type: string }>(payload)
      const name = this.nameAt(data.player_position)
      if (data.announcement_type === 'game') {
        toast('warning', t('toast.contraGame', { name }), 5000)
      } else {
        toast('warning', t('toast.contra', { name, what: t(`announcement.${data.announcement_type}`) }), 3500)
      }
    })

    socket.on('recontra_made', (payload) => {
      const data = unwrap<{ player_position: number; announcement_type: string }>(payload)
      toast('warning', t('toast.recontra', {
        name: this.nameAt(data.player_position),
        what: t(`announcement.${data.announcement_type}`),
      }), 3500)
    })

    socket.on('card_played', () => playSound('card'))

    socket.on('trick_complete', (payload) => {
      const data = unwrap<{ winner: number; trick_number: number; cards?: TrickCard[] }>(payload)
      const cards = data.cards || store().gameState?.current_trick || []
      if (!cards.length) return
      store().setFinishedTrick({ cards, winner: Number(data.winner), trick_number: data.trick_number })
      playSound('trick')
      if (this.trickTimer) clearTimeout(this.trickTimer)
      this.trickTimer = setTimeout(() => store().setFinishedTrick(null), TRICK_SHOW_MS)
    })

    socket.on('game_over', (payload) => {
      store().setGameOverData(unwrap<GameOverData>(payload))
    })

    // ---- chat -------------------------------------------------------------

    socket.on('chat_history', (data: { messages?: any[] }) => {
      store().clearChatMessages()
      ;(data.messages || []).forEach((msg) => store().addChatMessage(this.toChat(msg)))
    })

    socket.on('chat_message', (msg) => {
      const own = msg.player_name === store().playerName
      store().addChatMessage(this.toChat(msg), !own)
    })

    // ---- errors -----------------------------------------------------------

    socket.on('error', (payload) => {
      const data = unwrap<{ code?: string; message?: string }>(payload) || {}
      const code = data.code || ''
      const message = data.message || ''

      if (code === 'JOIN_ROOM_ERROR') {
        // The table is gone or full: back to the lobby
        const key = /not found/i.test(message) ? 'error.roomGone' : /full/i.test(message) ? 'error.roomFull' : null
        store().resetRoomSession()
        toast('warning', key ? t(key) : message, 5000)
        this.listRooms()
        return
      }
      toast('error', t(`error.${code}`, { defaultValue: message || t('error.generic') }))
    })
  }

  private toChat(msg: any) {
    return {
      id: msg.id || Math.random().toString(36).substring(7),
      player_name: msg.player_name,
      message: msg.message,
      timestamp: msg.timestamp || Date.now(),
    }
  }

  private nameAt(position: number): string {
    const fromGame = store().gameState?.players.find((p) => p.position === position)?.name
    const fromRoom = store().roomState?.players.find((p) => p.position === position)?.name
    return fromGame || fromRoom || `#${position + 1}`
  }

  disconnect() {
    this.socket?.disconnect()
    this.socket = null
    store().setConnectionStatus('disconnected')
  }

  // ---- emit ---------------------------------------------------------------

  private emit(event: string, data: Record<string, unknown> = {}) {
    this.socket?.emit(event, data)
  }

  listRooms() {
    this.emit('list_rooms')
  }

  createRoom(withBots = false) {
    store().setQuickBots(withBots)
    this.emit('create_room', { player_name: store().playerName })
  }

  joinRoom(roomId: string) {
    const { playerName, playerId } = store()
    this.emit('join_room', { player_name: playerName, player_id: playerId, room_id: roomId })
  }

  leaveRoom() {
    this.emit('leave_room')
    store().resetRoomSession()
    this.listRooms()
  }

  ready(ready = true) {
    this.emit('ready', { ready })
  }

  nextHand() {
    this.emit('next_hand')
  }

  swapSeats(from: number, to: number) {
    this.emit('swap_seats', { from_position: from, to_position: to })
  }

  addBot(position: number) {
    this.emit('add_bot', { position })
  }

  removeBot(position: number) {
    this.emit('remove_bot', { position })
  }

  fillBots() {
    this.emit('fill_bots')
  }

  replaceWithBot(position: number) {
    this.emit('replace_with_bot', { position })
  }

  setBotSpeed(speed: BotSpeed) {
    this.emit('set_bot_speed', { speed })
  }

  placeBid(bidType: string) {
    this.emit('place_bid', { bid_type: bidType })
  }

  discardCards(cardIds: string[]) {
    store().clearSelectedCards()
    this.emit('discard_cards', { card_ids: cardIds })
  }

  callPartner(tarokkRank: string) {
    this.emit('call_partner', { tarokk_rank: tarokkRank })
  }

  makeAnnouncements(announcementTypes: string[]) {
    this.emit('make_announcement', { announcement_types: announcementTypes, announced: true })
  }

  passAnnouncement() {
    this.emit('pass_announcement')
  }

  contraAnnouncement(announcementType: string) {
    this.emit('contra_announcement', { announcement_type: announcementType })
  }

  recontraAnnouncement(announcementType: string) {
    this.emit('recontra_announcement', { announcement_type: announcementType })
  }

  playCard(cardId: string) {
    store().clearSelectedCards()
    this.emit('play_card', { card_id: cardId })
  }

  sendChatMessage(message: string) {
    this.emit('send_chat_message', { player_name: store().playerName, message })
  }
}

// Singleton instance
export const socketManager = new SocketManager()

// Handy when testing by hand in the browser console (development only)
if (import.meta.env.DEV) {
  ;(window as any).__tarokk = { socketManager, store: useGameStore }
}
