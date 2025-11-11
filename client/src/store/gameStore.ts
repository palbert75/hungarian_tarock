import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type {
  ConnectionStatus,
  GameState,
  RoomState,
  AvailableRoom,
  YourTurnData,
  Card,
  ModalType,
  ToastMessage,
} from '@/types'

interface GameStore {
  // Connection state
  connectionStatus: ConnectionStatus
  playerId: string | null
  playerName: string
  playerPosition: number | null

  // Room state
  roomState: RoomState | null
  availableRooms: AvailableRoom[]

  // Game state
  gameState: GameState | null
  yourTurnData: YourTurnData | null

  // UI state
  selectedCards: string[]
  hoveredCard: string | null
  showingModal: ModalType
  toasts: ToastMessage[]
  soundEnabled: boolean
  musicEnabled: boolean

  // Actions - Connection
  setConnectionStatus: (status: ConnectionStatus) => void
  setPlayerInfo: (id: string, name: string) => void
  setPlayerPosition: (position: number) => void

  // Actions - Room
  setRoomState: (roomState: RoomState | null) => void
  setAvailableRooms: (rooms: AvailableRoom[]) => void

  // Actions - Game
  setGameState: (gameState: GameState | null) => void
  setYourTurnData: (data: YourTurnData | null) => void

  // Actions - UI
  toggleCardSelection: (cardId: string) => void
  clearSelectedCards: () => void
  setHoveredCard: (cardId: string | null) => void
  setShowingModal: (modal: ModalType) => void
  addToast: (toast: Omit<ToastMessage, 'id'>) => void
  removeToast: (id: string) => void
  toggleSound: () => void
  toggleMusic: () => void

  // Helpers
  getMyHand: () => Card[]
  isMyTurn: () => boolean
  getPlayerAtPosition: (position: number) => any
}

// Use sessionStorage for development (multi-tab testing) or localStorage for production
// sessionStorage is isolated per tab, localStorage is shared across tabs
const useSessionStorage = import.meta.env.DEV // Use sessionStorage in dev mode

export const useGameStore = create<GameStore>()(
  persist(
    (set, get) => ({
      // Initial state
      connectionStatus: 'disconnected',
      playerId: null,
      playerName: '',
      playerPosition: null,
      roomState: null,
      availableRooms: [],
      gameState: null,
      yourTurnData: null,
      selectedCards: [],
      hoveredCard: null,
      showingModal: null,
      toasts: [],
      soundEnabled: true,
      musicEnabled: false,

  // Connection actions
  setConnectionStatus: (status) => set({ connectionStatus: status }),

  setPlayerInfo: (id, name) => set({ playerId: id, playerName: name }),

  setPlayerPosition: (position) => set({ playerPosition: position }),

  // Room actions
  setRoomState: (roomState) => set({ roomState }),

  setAvailableRooms: (rooms) => set({ availableRooms: rooms }),

  // Game actions
  setGameState: (gameState) => set({ gameState }),

  setYourTurnData: (data) => set({ yourTurnData: data }),

  // UI actions
  toggleCardSelection: (cardId) => {
    const { selectedCards } = get()
    const isSelected = selectedCards.includes(cardId)

    set({
      selectedCards: isSelected
        ? selectedCards.filter((id) => id !== cardId)
        : [...selectedCards, cardId],
    })
  },

  clearSelectedCards: () => set({ selectedCards: [] }),

  setHoveredCard: (cardId) => set({ hoveredCard: cardId }),

  setShowingModal: (modal) => set({ showingModal: modal }),

  addToast: (toast) => {
    const id = Math.random().toString(36).substring(7)
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }))

    // Auto-remove after duration
    const duration = toast.duration || 3000
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }))
    }, duration)
  },

  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }))
  },

  toggleSound: () => {
    set((state) => ({ soundEnabled: !state.soundEnabled }))
  },

  toggleMusic: () => {
    set((state) => ({ musicEnabled: !state.musicEnabled }))
  },

  // Helpers
  getMyHand: () => {
    const { gameState, playerPosition } = get()
    if (!gameState || playerPosition === null) return []

    const me = gameState.players[playerPosition]
    return me?.hand || []
  },

  isMyTurn: () => {
    const { gameState, playerPosition } = get()
    if (!gameState || playerPosition === null) return false

    return gameState.current_turn === playerPosition
  },

  getPlayerAtPosition: (position) => {
    const { gameState } = get()
    if (!gameState) return null

    return gameState.players[position]
  },
    }),
    {
      name: 'tarokk-game-storage',
      // Use sessionStorage in dev mode (per-tab), localStorage in production (persistent)
      storage: useSessionStorage
        ? {
            getItem: (name) => {
              const value = sessionStorage.getItem(name)
              return value ? JSON.parse(value) : null
            },
            setItem: (name, value) => {
              sessionStorage.setItem(name, JSON.stringify(value))
            },
            removeItem: (name) => {
              sessionStorage.removeItem(name)
            },
          }
        : undefined, // undefined = use default localStorage
      partialize: (state) => ({
        playerId: state.playerId,
        playerName: state.playerName,
        playerPosition: state.playerPosition,
        roomState: state.roomState,
        gameState: state.gameState,
        soundEnabled: state.soundEnabled,
        musicEnabled: state.musicEnabled,
      }),
    }
  )
)
