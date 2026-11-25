import { describe, expect, it } from 'vitest'
import type { TFunction } from 'i18next'
import hu from '@/i18n/hu.json'
import { cardShortName, usualCall } from './cardNames'

// A stand-in for the translator: looks the key up in the Hungarian texts
const t = ((key: string, options?: { defaultValue?: string }) => {
  const found = key.split('.').reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], hu)
  return typeof found === 'string' ? found : options?.defaultValue ?? key
}) as unknown as TFunction

describe('card names', () => {
  it('names the lowest card a ten in the black suits and an ace in the red ones', () => {
    expect(cardShortName({ suit: 'spades', rank: '10' }, t)).toBe('♠10')
    expect(cardShortName({ suit: 'clubs', rank: '10' }, t)).toBe('♣10')
    expect(cardShortName({ suit: 'hearts', rank: '10' }, t)).toBe('♥Á')
    expect(cardShortName({ suit: 'diamonds', rank: '10' }, t)).toBe('♦Á')
  })

  it('leaves the other cards as they were', () => {
    expect(cardShortName({ suit: 'hearts', rank: 'K' }, t)).toBe('♥K')
    expect(cardShortName({ suit: 'tarokk', rank: 'X' }, t)).toBe('X')
    expect(cardShortName({ suit: 'tarokk', rank: 'skiz' }, t)).toBe('Skíz')
  })
})

describe('usualCall', () => {
  it('calls the XX when the declarer does not hold it', () => {
    expect(usualCall(new Set(['XXI', 'XIX']))).toBe('XX')
  })
  it('calls the XV when the declarer holds XX down to XVI', () => {
    expect(usualCall(new Set(['XXI', 'XX', 'XIX', 'XVIII', 'XVII', 'XVI']))).toBe('XV')
  })
})
