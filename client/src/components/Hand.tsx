import { useMemo } from 'react'
import type { CSSProperties } from 'react'
import Card from './Card'
import type { Card as CardType } from '@/types'
import { sortCards } from '@/utils/cardSorting'

interface HandGridProps {
  cards: CardType[]
  selected?: string[]
  /** Card ids that cannot be chosen now (shown greyed) */
  disabled?: string[]
  /** Card ids carrying a small tag (e.g. "new" for talon cards) */
  tagged?: string[]
  tagLabel?: string
  /** Card ids the tutorial recommends */
  hinted?: string[]
  onTap?: (cardId: string) => void
  /** A card flicked upwards (thrown onto the table) */
  onSwipeUp?: (cardId: string) => void
  swipeDirection?: 'up' | 'left'
}

/** Split sorted cards into two rows that are as even as possible (one row for few cards). */
export function splitRows(cards: CardType[]): CardType[][] {
  if (cards.length <= 4) return [cards]
  const first = Math.ceil(cards.length / 2)
  return [cards.slice(0, first), cards.slice(first)]
}

/** The hand, large: it fills whatever space its parent gives it. */
export function HandGrid({ cards, selected = [], disabled = [], tagged = [], tagLabel, hinted = [], onTap, onSwipeUp, swipeDirection }: HandGridProps) {
  const rows = useMemo(() => splitRows(sortCards(cards)), [cards])
  const cols = Math.max(...rows.map((r) => r.length), 1)
  const style = { '--cols': cols, '--rows': rows.length } as CSSProperties

  return (
    <div className="hand-box" style={style}>
      {rows.map((row, i) => (
        <div className="hand-row" key={i}>
          {row.map((card) => {
            const isDisabled = disabled.includes(card.id)
            return (
              <Card
                key={card.id}
                card={card}
                selected={selected.includes(card.id)}
                dimmed={isDisabled}
                hinted={hinted.includes(card.id)}
                tag={tagged.includes(card.id) ? tagLabel : undefined}
                onClick={onTap && !isDisabled ? () => onTap(card.id) : undefined}
                onSwipeUp={onSwipeUp && !isDisabled ? () => onSwipeUp(card.id) : undefined}
                swipeDirection={swipeDirection}
              />
            )
          })}
        </div>
      ))}
    </div>
  )
}

/** The hand, small: one overlapping row along the bottom. */
export function HandStrip({ cards, onTap, label }: { cards: CardType[]; onTap?: () => void; label?: string }) {
  const sorted = useMemo(() => sortCards(cards), [cards])
  const n = Math.max(sorted.length, 1)
  // Overlap so that any number of cards fits the width
  const width = `min(3.1rem, calc((100vw - 1.5rem) / ${n} * 1.35))`
  const overlap = `calc(${width} * -0.27)`
  return (
    <button type="button" onClick={onTap} className="w-full flex flex-col items-center gap-1 py-1" aria-label={label}>
      {label && <span className="text-[0.7rem] text-slate-300/80">{label}</span>}
      <div className="flex justify-center" style={{ paddingLeft: `calc(${width} * 0.27)` }}>
        {sorted.map((card) => (
          <div key={card.id} style={{ marginLeft: overlap }}>
            <Card card={card} width={width} />
          </div>
        ))}
      </div>
    </button>
  )
}
