import type { Table } from './useTable'

export type Side = 'declarer' | 'opponent' | 'unknown'
/** A seat as I see it: on my side, against me, or not known yet */
export type Relation = 'ally' | 'enemy' | 'unknown'

interface Sides {
  mySide: Side
  sideOf: (position: number) => Side
  /** Blue for my side, red for the other, as far as I can know it */
  relationOf: (position: number) => Relation
  known: boolean
}

/**
 * Which side each seat is on, as far as I can know it: the declarer always,
 * the partner once the called card showed (or when I hold it myself).
 */
export function useSides(table: Table): Sides {
  const { game, me, myHand } = table
  const declarer = game.declarer_position
  if (declarer === null || declarer === undefined || game.phase === 'bidding') {
    return { mySide: 'unknown', sideOf: () => 'unknown', relationOf: () => 'unknown', known: false }
  }
  const called = (game.called_card_rank || '').toLowerCase()
  const iHoldCalled = !!called && myHand.some((c) => c.suit === 'tarokk' && c.rank.toLowerCase() === called)
  // An accepted invit or a yielded game tells the whole table who the partner is
  const shownPartner = game.partner_revealed ? game.partner_position : game.convention_partner ?? null
  const partnerKnown = shownPartner !== null && shownPartner !== undefined
  const iAmPartner = (partnerKnown && shownPartner === me) || iHoldCalled
  const mySide: Side = me === declarer || iAmPartner ? 'declarer' : 'opponent'

  const sideOf = (position: number): Side => {
    if (position === me) return mySide
    if (position === declarer) return 'declarer'
    if (partnerKnown && position === shownPartner) return 'declarer'
    // Everyone else is a defender once both declarer-side seats are known to me
    if (iAmPartner || game.declarer_alone || partnerKnown) return 'opponent'
    return 'unknown'
  }
  const relationOf = (position: number): Relation => {
    const side = sideOf(position)
    if (side === 'unknown') return 'unknown'
    return side === mySide ? 'ally' : 'enemy'
  }
  return { mySide, sideOf, relationOf, known: true }
}
