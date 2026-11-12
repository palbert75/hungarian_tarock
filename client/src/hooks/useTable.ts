import { useMemo } from 'react'
import { selectIsOwner, selectMyPosition, useGameStore } from '@/store/gameStore'
import type { Card, GameState, Player, Seat } from '@/types'
import { positionAt, screenSeat } from '@/utils/seats'

export interface Table {
  game: GameState
  me: number
  myPlayer: Player
  myHand: Card[]
  isMyTurn: boolean
  isOwner: boolean
  /** Player on the seat with this table position */
  playerAt: (position: number) => Player | undefined
  /** Screen seat (S/E/N/W) of a table position */
  seatOf: (position: number) => Seat
  /** Table position shown at a screen seat */
  positionAt: (seat: Seat) => number
  /** Name to show for a position ("You" is handled by SeatLabel) */
  nameAt: (position: number) => string
}

/** Everything a game screen needs about the table, seen from my seat. */
export function useTable(): Table | null {
  const game = useGameStore((s) => s.gameState)
  const me = useGameStore(selectMyPosition)
  const isOwner = useGameStore(selectIsOwner)

  return useMemo(() => {
    if (!game || me === null) return null
    const playerAt = (position: number) => game.players.find((p) => p.position === position)
    const myPlayer = playerAt(me)
    if (!myPlayer) return null
    return {
      game,
      me,
      myPlayer,
      myHand: myPlayer.hand || [],
      isMyTurn: game.current_turn === me,
      isOwner,
      playerAt,
      seatOf: (position: number) => screenSeat(position, me),
      positionAt: (seat: Seat) => positionAt(seat, me),
      nameAt: (position: number) => playerAt(position)?.name || `#${position + 1}`,
    }
  }, [game, me, isOwner])
}
