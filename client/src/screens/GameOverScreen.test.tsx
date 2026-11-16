import { describe, expect, it, vi } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import type { Table } from '@/hooks/useTable'
import type { GameOverData, GameState } from '@/types'
import GameOverScreen from './GameOverScreen'

// The page is rendered without a server and without a browser: texts show as their keys
vi.mock('@/services/socketManager', () => ({ socketManager: {} }))
vi.mock('@/components/ReportSheet', () => ({ default: () => null }))
const store: Record<string, unknown> = { roomState: null, addToast: () => undefined }
vi.mock('@/store/gameStore', () => ({
  useGameStore: (select: (state: Record<string, unknown>) => unknown) => select(store),
}))

// Problem report 20261116-070517: the declarer's side (seats 3 and 1) won the game for 1 point
// but lost trull, four kings and a silent pagát ulti, so the defenders ended 8 points up.
const reported = {
  declarer: 3,
  partner: 1,
  declarer_alone: false,
  declarer_team_points: 59,
  opponent_team_points: 35,
  winner: 'declarer_team',
  base_game_value: 1,
  game_multiplier: 1,
  final_game_value: 1,
  game_contra: false,
  player_scores: { '0': 58, '1': 42, '2': 58, '3': 42 },
  total_scores: [8, -8, 8, -8],
  hand_number: 1,
  announcement_details: [],
  tarokk_declarations: [],
} as unknown as GameOverData

function headline(me: number, result: GameOverData): string {
  store.gameOverData = result
  const players = [0, 1, 2, 3].map((position) => ({ position, name: `P${position}`, total_score: 0 }))
  const table = {
    game: { players, trick_history: [] } as unknown as GameState,
    me,
    nameAt: (position: number) => `P${position}`,
  } as unknown as Table
  const html = renderToStaticMarkup(<GameOverScreen table={table} />)
  return html.match(/text-2xl font-bold">(.*?)<\/div>/)![1].replace(/<[^>]+>/g, '')
}

describe('headline of the end-of-hand page', () => {
  it('says "won" to the loser of the game who was paid more on the bonuses', () => {
    expect(headline(0, reported)).toBe('over.youWon (+8)')
  })

  it('says "lost" to the winner of the game who paid more on the bonuses', () => {
    expect(headline(3, reported)).toBe('over.youLost (-8)')
  })

  it('says "draw" when the hand cost and brought me nothing', () => {
    const even = { ...reported, player_scores: { '0': 50, '1': 50, '2': 50, '3': 50 } } as GameOverData
    expect(headline(0, even)).toBe('over.draw (0)')
  })
})
