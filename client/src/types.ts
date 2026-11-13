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
  contra?: boolean
  recontra?: boolean
  contra_by?: number | null
  recontra_by?: number | null
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
  is_bot?: boolean
  bot_controlled?: boolean
  vacant?: boolean
  total_score?: number
  ready_next?: boolean
  total_points: number
  tricks_won_count: number
  hand?: Card[] // Only visible for your own hand
  talon_card_ids?: string[] // Cards you received from the talon this hand
  /** How many tarokks this player put into the skart (declared at the table) */
  tarokks_discarded?: number
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

/** The trick that was just completed, shown briefly before it is collected. */
export interface FinishedTrick {
  cards: TrickCard[]
  winner: number
  trick_number: number
}

export interface GameState {
  game_id: string
  phase: GamePhase
  players: Player[]
  dealer_position: number
  current_turn: number
  bid_history: Bid[]
  winning_bid?: Bid | null
  declarer_position: number | null
  partner_position: number | null
  partner_revealed: boolean
  called_card_rank?: string | null
  trick_number: number
  trick_leader?: number | null
  current_trick: TrickCard[]
  talon: Card[]
  announcements: Announcement[]
  trick_history: CompletedTrick[]
  players_who_discarded?: number[]
  announcement_history?: (Announcement | null)[]
  announcement_turn_log?: { position: number; passed: boolean }[]
  game_contra?: boolean
  game_contra_by?: number | null
  declarer_alone?: boolean
  hand_number?: number
}

export interface RoomPlayer {
  id: string
  name: string
  position: number
  is_connected: boolean
  is_ready: boolean
  ready_next?: boolean
  is_bot?: boolean
  bot_controlled?: boolean
  total_score?: number
}

export type BotSpeed = 'fast' | 'normal' | 'slow'

export interface RoomState {
  room_id: string
  owner_id?: string | null
  bot_speed?: BotSpeed
  phase?: GamePhase
  hand_number?: number
  players: RoomPlayer[]
  is_full: boolean
  game_started: boolean
}

export type AvailableRoom = RoomState

export type ConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'error'

/** A recommended action with a translatable reason (tutorial hint). */
export interface Hint {
  action: 'bid' | 'discard' | 'call_partner' | 'announce' | 'pass_announcement' | 'contra' | 'play_card'
  payload: {
    bid_type?: BidType
    card_ids?: string[]
    tarokk_rank?: string
    announcement_types?: AnnouncementType[]
    announcement_type?: AnnouncementType
    card_id?: string
  }
  reason_key: string
  reason_params: Record<string, unknown>
}

export interface YourTurnData {
  valid_actions: string[]
  valid_bids?: BidType[]
  valid_announcements?: AnnouncementType[]
  valid_cards?: string[]
  discard_count?: number
  hint?: Hint
}

export interface GameOverData {
  declarer: number
  partner: number | null
  declarer_alone?: boolean
  declarer_team_points: number
  opponent_team_points: number
  winner: 'declarer_team' | 'opponent_team'
  base_game_value: number
  game_multiplier: number
  final_game_value: number
  game_contra?: boolean
  player_scores: Record<string, number>
  total_scores?: number[]
  hand_number?: number
  announcement_details: {
    type: AnnouncementType
    player_position: number
    announced: boolean
    points: number
    multiplier?: number
    team?: 'declarer_team' | 'opponent_team'
    achieved: boolean
    contra?: boolean
    recontra?: boolean
  }[]
}

// UI-specific types

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

export type Seat = 'S' | 'E' | 'N' | 'W'
