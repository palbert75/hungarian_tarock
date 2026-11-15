import type { TFunction } from 'i18next'
import type { Card, Suit } from '@/types'

export const SUIT_SYMBOL: Record<Suit, string> = {
  hearts: '♥',
  diamonds: '♦',
  clubs: '♣',
  spades: '♠',
  tarokk: '',
}

/** Rank as printed on the card face: "Skíz", "XXI", "K", "D"… */
export function rankLabel(card: Pick<Card, 'suit' | 'rank'>, t: TFunction): string {
  if (card.suit === 'tarokk') {
    return card.rank.toLowerCase() === 'skiz' ? t('card.skiz') : card.rank
  }
  // The lowest card is a ten in the black suits and an ace in the red ones.
  // The game knows both as rank "10"; only the name differs.
  if (card.rank === '10' && isRedSuit(card.suit)) return t('card.rank.ace')
  return t(`card.rank.${card.rank}`, { defaultValue: card.rank })
}

export function isRedSuit(suit: Suit): boolean {
  return suit === 'hearts' || suit === 'diamonds'
}

/** Short name for buttons and hints: "XVII", "Skíz", "♥K". */
export function cardShortName(card: Pick<Card, 'suit' | 'rank'>, t: TFunction): string {
  return `${SUIT_SYMBOL[card.suit]}${rankLabel(card, t)}`
}

/** A tarokk rank on its own ("XX", "skiz") as a display name. */
export function tarokkName(rank: string, t: TFunction): string {
  return rankLabel({ suit: 'tarokk', rank }, t)
}

/** May this card go into the skart? (kings, honours and the XX may not) */
export function canDiscard(card: Card): boolean {
  if (card.card_type === 'king' || card.card_type === 'honour') return false
  if (card.suit === 'tarokk') {
    const rank = card.rank.toLowerCase()
    return !['skiz', 'xxi', 'i', 'xx'].includes(rank)
  }
  return card.rank !== 'K'
}
