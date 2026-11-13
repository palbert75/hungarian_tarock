import type { Table } from './useTable'

export type Side = 'declarer' | 'opponent' | 'unknown'

/**
 * Which side each seat is on, as far as I can know it: the declarer always,
 * the partner once the called card showed (or when I hold it myself).
 */
export function useSides(table: Table): { mySide: Side; sideOf: (position: number) => Side; known: boolean } {
  const { game, me, myHand } = table
  const declarer = game.declarer_position
  if (declarer === null || declarer === undefined || game.phase === 'bidding') {
    return { mySide: 'unknown', sideOf: () => 'unknown', known: false }
  }
  const called = (game.called_card_rank || '').toLowerCase()
  const iHoldCalled = !!called && myHand.some((c) => c.suit === 'tarokk' && c.rank.toLowerCase() === called)
  const iAmPartner = (game.partner_revealed && game.partner_position === me) || iHoldCalled
  const mySide: Side = me === declarer || iAmPartner ? 'declarer' : 'opponent'

  const sideOf = (position: number): Side => {
    if (position === me) return mySide
    if (position === declarer) return 'declarer'
    if (game.partner_revealed && position === game.partner_position) return 'declarer'
    // Everyone else is a defender once both declarer-side seats are known to me
    if (iAmPartner || game.declarer_alone || game.partner_revealed) return 'opponent'
    return 'unknown'
  }
  return { mySide, sideOf, known: true }
}
