import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type {
  ConnectionStatus,
  GameState,
  RoomState,
  AvailableRoom,
  YourTurnData,
  GameOverData,
  ToastMessage,
  ChatMessage,
  FinishedTrick,
} from '@/types'

interface GameStore {
  // Connection
  connectionStatus: ConnectionStatus
  playerId: string | null
  playerName: string
  /** Room we sit in (kept across reloads so we can come back to our seat) */
  roomId: string | null
  /** Room from an invite link, joined once we are connected */
  pendingRoomId: string | null
  /** "Play against bots": fill the new table with bots and start */
  quickBots: boolean

  // Room
  roomState: RoomState | null
  availableRooms: AvailableRoom[]

  // Game
  gameState: GameState | null
  yourTurnData: YourTurnData | null
  gameOverData: GameOverData | null
  finishedTrick: FinishedTrick | null

  // UI
  selectedCards: string[]
  toasts: ToastMessage[]
  chatMessages: ChatMessage[]
  unreadChat: number

  setConnectionStatus: (status: ConnectionStatus) => void
  setPlayerName: (name: string) => void
  setSeat: (playerId: string, roomId: string) => void
  setPendingRoomId: (roomId: string | null) => void
  setQuickBots: (on: boolean) => void

  setRoomState: (roomState: RoomState | null) => void
  setAvailableRooms: (rooms: AvailableRoom[]) => void
  resetRoomSession: () => void

  setGameState: (gameState: GameState | null) => void
  setYourTurnData: (data: YourTurnData | null) => void
  setGameOverData: (data: GameOverData | null) => void
  setFinishedTrick: (trick: FinishedTrick | null) => void

  toggleCardSelection: (cardId: string, max?: number) => void
  clearSelectedCards: () => void
  addToast: (toast: Omit<ToastMessage, 'id'>) => void
  removeToast: (id: string) => void

  addChatMessage: (message: ChatMessage, countUnread?: boolean) => void
  clearChatMessages: () => void
  markChatRead: () => void
}

// sessionStorage is isolated per tab (handy for testing four players in
// one browser); localStorage survives closing the app.
const storage = import.meta.env.DEV ? sessionStorage : localStorage

export const useGameStore = create<GameStore>()(
  persist(
    (set, get) => ({
      connectionStatus: 'disconnected',
      playerId: null,
      playerName: '',
      roomId: null,
      pendingRoomId: null,
      quickBots: false,
      roomState: null,
      availableRooms: [],
      gameState: null,
      yourTurnData: null,
      gameOverData: null,
      finishedTrick: null,
      selectedCards: [],
      toasts: [],
      chatMessages: [],
      unreadChat: 0,

      setConnectionStatus: (status) => set({ connectionStatus: status }),
      setPlayerName: (name) => set({ playerName: name }),
      setSeat: (playerId, roomId) => set({ playerId, roomId }),
      setPendingRoomId: (roomId) => set({ pendingRoomId: roomId }),
      setQuickBots: (on) => set({ quickBots: on }),

      setRoomState: (roomState) => set({ roomState }),
      setAvailableRooms: (rooms) => set({ availableRooms: rooms }),

      resetRoomSession: () =>
        set({
          playerId: null,
          roomId: null,
          quickBots: false,
          roomState: null,
          gameState: null,
          yourTurnData: null,
          gameOverData: null,
          finishedTrick: null,
          selectedCards: [],
          chatMessages: [],
          unreadChat: 0,
        }),

      setGameState: (gameState) => set({ gameState }),
      setYourTurnData: (data) => set({ yourTurnData: data }),
      setGameOverData: (data) => set({ gameOverData: data }),
      setFinishedTrick: (trick) => set({ finishedTrick: trick }),

      toggleCardSelection: (cardId, max) => {
        const { selectedCards } = get()
        if (selectedCards.includes(cardId)) {
          set({ selectedCards: selectedCards.filter((id) => id !== cardId) })
        } else if (max === 1) {
          set({ selectedCards: [cardId] })
        } else if (max === undefined || selectedCards.length < max) {
          set({ selectedCards: [...selectedCards, cardId] })
        }
      },
      clearSelectedCards: () => set({ selectedCards: [] }),

      addToast: (toast) => {
        const id = Math.random().toString(36).substring(7)
        // Keep at most three on screen
        set((state) => ({ toasts: [...state.toasts.slice(-2), { ...toast, id }] }))
        setTimeout(() => {
          set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
        }, toast.duration || 3000)
      },
      removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),

      addChatMessage: (message, countUnread = false) =>
        set((state) => ({
          chatMessages: [...state.chatMessages, message],
          unreadChat: countUnread ? state.unreadChat + 1 : state.unreadChat,
        })),
      clearChatMessages: () => set({ chatMessages: [], unreadChat: 0 }),
      markChatRead: () => set({ unreadChat: 0 }),
    }),
    {
      name: 'tarokk-game-storage',
      storage: createJSONStorage(() => storage),
      partialize: (state) => ({
        playerId: state.playerId,
        playerName: state.playerName,
        roomId: state.roomId,
      }),
    }
  )
)

/** My seat number at the table, from the room (it can change when seats are swapped). */
export function selectMyPosition(state: GameStore): number | null {
  const me = state.roomState?.players.find((p) => p.id === state.playerId)
  return me ? me.position : null
}

export function selectIsOwner(state: GameStore): boolean {
  return !!state.playerId && state.roomState?.owner_id === state.playerId
}
