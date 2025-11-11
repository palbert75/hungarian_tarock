import type { Card } from '@/types'

/**
 * Convert Roman numeral to integer for tarokk cards
 */
function romanToInt(roman: string): number {
  // Handle special names
  const lowerRoman = roman.toLowerCase()
  if (lowerRoman === 'škis' || lowerRoman === 'skis') return 22
  if (lowerRoman === 'pagát' || lowerRoman === 'pagat') return 1

  const romanValues: { [key: string]: number } = {
    I: 1,
    V: 5,
    X: 10,
    L: 50,
  }

  let result = 0
  let prevValue = 0

  for (let i = roman.length - 1; i >= 0; i--) {
    const char = roman[i]
    const value = romanValues[char] || 0

    if (value < prevValue) {
      result -= value
    } else {
      result += value
    }
    prevValue = value
  }

  return result
}

/**
 * Get numeric value for suit card rank (higher is better)
 */
function getSuitRankValue(rank: string): number {
  const rankValues: { [key: string]: number } = {
    K: 5, // King
    Q: 4, // Queen
    C: 3, // Cavalier
    J: 2, // Jack
  }

  // If it's a face card, return its value
  if (rankValues[rank]) {
    return rankValues[rank]
  }

  // If it's a number, return the number
  const num = parseInt(rank, 10)
  return isNaN(num) ? 0 : num / 10 // Divide by 10 so face cards are always higher
}

/**
 * Sort cards: Tarokks first (descending), then suits (descending within each suit)
 * Order: Hearts, Diamonds, Clubs, Spades
 */
export function sortCards(cards: Card[]): Card[] {
  const suitOrder = ['hearts', 'diamonds', 'clubs', 'spades']

  return [...cards].sort((a, b) => {
    // Tarokks come first
    if (a.suit === 'tarokk' && b.suit !== 'tarokk') return -1
    if (a.suit !== 'tarokk' && b.suit === 'tarokk') return 1

    // Both are tarokks - sort by rank descending
    if (a.suit === 'tarokk' && b.suit === 'tarokk') {
      const aValue = romanToInt(a.rank)
      const bValue = romanToInt(b.rank)
      return bValue - aValue // Descending (XXI before XX before XIX...)
    }

    // Both are suits - first sort by suit order
    const aSuitIndex = suitOrder.indexOf(a.suit)
    const bSuitIndex = suitOrder.indexOf(b.suit)

    if (aSuitIndex !== bSuitIndex) {
      return aSuitIndex - bSuitIndex
    }

    // Same suit - sort by rank descending
    const aRankValue = getSuitRankValue(a.rank)
    const bRankValue = getSuitRankValue(b.rank)
    return bRankValue - aRankValue // Descending (K before Q before C...)
  })
}
