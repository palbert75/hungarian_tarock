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
 * the partner once the called card showed (or when I hold it myself), or
 * earlier when the bidding, an announcement or a kontra gives the partner away.
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
  // At this table only the declarer's side announces; the defenders answer with kontra.
  // So a seat other than the declarer that announces (or says rekontra) is the partner,
  // and a seat that says kontra is a defender. I ignore it when I hold the called card.
  const others = [0, 1, 2, 3].filter((p) => p !== declarer && p !== me)
  let signalPartner: number | null = null
  if (!iHoldCalled) {
    const list = game.announcements || []
    const speaker = list.find((a) => a.announced !== false && others.includes(a.player_position))
    const rekontra = list.find((a) => a.recontra_by != null && others.includes(a.recontra_by))
    const kontra = list.find((a) => a.contra_by != null && others.includes(a.contra_by))
    if (speaker) signalPartner = speaker.player_position
    else if (rekontra) signalPartner = rekontra.recontra_by ?? null
    else if (kontra && me !== declarer && others.length === 2) {
      // I am a defender and so is the one who said kontra: the third seat is the partner
      signalPartner = others.find((p) => p !== kontra.contra_by) ?? null
    }
  }
  const shownPartner = game.partner_revealed
    ? game.partner_position
    : game.convention_partner ?? signalPartner ?? null
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
