import type { Seat } from '@/types'

/**
 * Where a player sits on my screen.
 *
 * I am always at the bottom (S). Tarokk is played counter-clockwise, so the
 * player who plays after me sits on my right (E), then across (N), then on
 * my left (W).
 */
export function screenSeat(absolute: number, me: number): Seat {
  const relative = (((absolute - me) % 4) + 4) % 4
  return (['S', 'E', 'N', 'W'] as const)[relative]
}

/** The table position shown at a screen seat. */
export function positionAt(seat: Seat, me: number): number {
  const relative = { S: 0, E: 1, N: 2, W: 3 }[seat]
  return (me + relative) % 4
}

export const SEATS: Seat[] = ['N', 'W', 'E', 'S']
