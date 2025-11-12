/**
 * Type definitions for Hungarian Tarokk client
 */

export type Suit = 'tarokk' | 'hearts' | 'diamonds' | 'spades' | 'clubs'

export type CardType = 'honour' | 'king' | 'queen' | 'cavalier' | 'jack' | 'tarokk' | 'suit'

export interface Card {
  id: string
  suit: Suit
  rank: string
  card_type: CardType
  points: number
}

export type GamePhase =
  | 'waiting'
  | 'dealing'
  | 'bidding'
  | 'talon_distribution'
  | 'discarding'
  | 'partner_call'
  | 'announcements'
  | 'playing'
  | 'scoring'
  | 'game_end'

export type BidType = 'pass' | 'three' | 'two' | 'one' | 'solo' | 'hold'

export interface Bid {
  player_position: number
  bid_type: BidType
  game_value: number
  talon_cards: number
}

export type AnnouncementType =
  | 'trull'
  | 'four_kings'
  | 'double_game'
  | 'volat'
  | 'pagat_ultimo'
  | 'xxi_catch'

export interface Announcement {
  player_position: number
  announcement_type: AnnouncementType
  announced: boolean
  points: number
  multiplier: number
}

export interface Player {
  id: string
  name: string
  position: number
  hand_size: number
  is_connected: boolean
  is_ready: boolean
  is_declarer: boolean
  is_partner?: boolean
  total_points: number
  tricks_won_count: number
  hand?: Card[] // Only visible for your own hand
}

export interface TrickCard {
  player_position: number
  card: Card
}

export interface CompletedTrick {
  trick_number: number
  cards: TrickCard[]
  winner: number
  winner_name: string
  lead_suit: string | null
}

export interface GameState {
  game_id: string
  phase: GamePhase
  players: Player[]
  dealer_position: number
  current_turn: number
  bid_history: Bid[]
  declarer_position: number | null
  partner_position: number | null
  partner_revealed: boolean
  trick_number: number
  current_trick: TrickCard[]
  talon: Card[]
  announcements: Announcement[]
  trick_history: CompletedTrick[]
}

export interface RoomState {
  room_id: string
  players: Array<{
    name: string
    position: number
    is_connected: boolean
    is_ready: boolean
  }>
  is_full: boolean
  game_started: boolean
}

export interface AvailableRoom {
  room_id: string
  players: Array<{
    id: string
    name: string
    position: number
    is_ready: boolean
    is_connected: boolean
  }>
  is_full: boolean
  game_started: boolean
}

export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'

export interface YourTurnData {
  valid_actions: string[]
  valid_bids?: BidType[]
  valid_announcements?: AnnouncementType[]
  valid_cards?: string[]
}

// UI-specific types

export type ModalType = 'rules' | 'settings' | 'score' | null

export interface ToastMessage {
  id: string
  type: 'success' | 'error' | 'info' | 'warning'
  message: string
  duration?: number
}

export interface ChatMessage {
  id: string
  player_name: string
  message: string
  timestamp: number
}
