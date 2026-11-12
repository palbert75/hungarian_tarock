import { describe, expect, it } from 'vitest'
import { positionAt, screenSeat } from './seats'

describe('screenSeat', () => {
  it('puts me at the bottom whatever my seat number is', () => {
    for (let me = 0; me < 4; me++) expect(screenSeat(me, me)).toBe('S')
  })

  it('puts the next player (counter-clockwise) on my right', () => {
    for (let me = 0; me < 4; me++) {
      expect(screenSeat((me + 1) % 4, me)).toBe('E')
      expect(screenSeat((me + 2) % 4, me)).toBe('N')
      expect(screenSeat((me + 3) % 4, me)).toBe('W')
    }
  })

  it('is the inverse of positionAt for all 16 combinations', () => {
    for (let me = 0; me < 4; me++) {
      for (let abs = 0; abs < 4; abs++) {
        expect(positionAt(screenSeat(abs, me), me)).toBe(abs)
      }
    }
  })
})
