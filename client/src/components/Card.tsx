import { useRef, useState } from 'react'
import type { PointerEvent as ReactPointerEvent } from 'react'
import { useTranslation } from 'react-i18next'
import type { Card as CardType } from '@/types'
import { SUIT_SYMBOL, rankLabel } from '@/utils/cardNames'

interface CardProps {
  card: CardType
  /** Fixed width (CSS length). Inside a hand the width comes from the hand's layout. */
  width?: string
  selected?: boolean
  dimmed?: boolean
  winner?: boolean
  hinted?: boolean
  tag?: string
  onClick?: () => void
  /** Called when the card is flicked towards the table, like throwing it there */
  onSwipeUp?: () => void
  /** Where the table lies from the hand: above it (phones) or to its left (wide screens) */
  swipeDirection?: 'up' | 'left'
  className?: string
}

/** How far towards the table (as a share of the card's height) a card must travel to count as thrown */
const THROW_SHARE = 0.4
const THROW_MIN_PX = 36

const colorOf = (suit: string): string =>
  suit === 'hearts' || suit === 'diamonds' ? '#b91c1c' : suit === 'tarokk' ? '#3730a3' : '#111827'

/** Painted card faces live in public/cards (made by scripts/slice-cards.py). */
const artOf = (card: CardType): string =>
  `/cards/${card.suit}-${card.suit === 'tarokk' && card.rank.toLowerCase() === 'skiz' ? 'skiz' : card.rank}.webp`

/** A playing card. The painted face is used when it loads; the drawn one is the fallback. */
export default function Card({ card, width, selected, dimmed, winner, hinted, tag, onClick, onSwipeUp, swipeDirection = 'up', className = '' }: CardProps) {
  const { t } = useTranslation()
  const [artFailed, setArtFailed] = useState(false)
  // Swipe up to throw: the card follows the finger, flies off when released far enough
  const drag = useRef<{ id: number; x: number; y: number; height: number; moved: boolean } | null>(null)
  const swallowClick = useRef(false)
  const [offset, setOffset] = useState<{ x: number; y: number } | null>(null)
  const [thrown, setThrown] = useState(false)

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (!onSwipeUp || thrown || (e.pointerType === 'mouse' && e.button !== 0)) return
    drag.current = { id: e.pointerId, x: e.clientX, y: e.clientY, height: e.currentTarget.offsetHeight, moved: false }
    swallowClick.current = false
    e.currentTarget.setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const d = drag.current
    if (!d || d.id !== e.pointerId) return
    const left = swipeDirection === 'left'
    // Free along the throw direction (towards the table only), damped across it
    const dx = left ? Math.min(0, e.clientX - d.x) : (e.clientX - d.x) * 0.5
    const dy = left ? (e.clientY - d.y) * 0.5 : Math.min(0, e.clientY - d.y)
    if (!d.moved && Math.hypot(dx, dy) < 8) return
    d.moved = true
    setOffset({ x: dx, y: dy })
  }
  const endDrag = (e: ReactPointerEvent<HTMLDivElement>, cancelled: boolean) => {
    const d = drag.current
    if (!d || d.id !== e.pointerId) return
    drag.current = null
    if (!d.moved) return
    swallowClick.current = true
    const travel = swipeDirection === 'left' ? d.x - e.clientX : d.y - e.clientY
    if (!cancelled && travel >= Math.max(THROW_MIN_PX, d.height * THROW_SHARE)) {
      setThrown(true)
      onSwipeUp?.()
      // If the play is refused the card comes back
      window.setTimeout(() => {
        setThrown(false)
        setOffset(null)
      }, 900)
    } else {
      setOffset(null)
    }
  }
  const swipeStyle = thrown
    ? {
        transform:
          swipeDirection === 'left'
            ? `translate(-260%, ${offset?.y ?? 0}px) scale(0.8)`
            : `translate(${offset?.x ?? 0}px, -160%) scale(0.8)`,
        opacity: 0,
        transition: 'transform 220ms ease-in, opacity 220ms ease-in',
      }
    : offset
      ? { transform: `translate(${offset.x}px, ${offset.y}px)`, transition: 'none', zIndex: 20 }
      : undefined
  const isTarokk = card.suit === 'tarokk'
  const label = rankLabel(card, t)
  const symbol = SUIT_SYMBOL[card.suit]
  const color = colorOf(card.suit)
  // Long labels ("XVIII", "Skíz") get a smaller print so they fit
  const centerSize = isTarokk ? (label.length >= 5 ? '24cqw' : label.length === 4 ? '29cqw' : '36cqw') : '46cqw'

  return (
    <div
      role={onClick ? 'button' : undefined}
      aria-label={`${symbol}${label}`}
      aria-pressed={onClick ? !!selected : undefined}
      aria-disabled={dimmed || undefined}
      onClick={
        onClick
          ? () => {
              if (swallowClick.current) {
                swallowClick.current = false
                return
              }
              onClick()
            }
          : undefined
      }
      onPointerDown={onSwipeUp ? onPointerDown : undefined}
      onPointerMove={onSwipeUp ? onPointerMove : undefined}
      onPointerUp={onSwipeUp ? (e) => endDrag(e, false) : undefined}
      onPointerCancel={onSwipeUp ? (e) => endDrag(e, true) : undefined}
      style={{ ...(width ? { width } : {}), ...(onSwipeUp ? { touchAction: 'none' } : {}), ...swipeStyle }}
      className={[
        'tcard',
        isTarokk ? 'tcard-tarokk' : '',
        dimmed ? 'tcard-dim' : '',
        selected ? 'tcard-selected' : '',
        winner ? 'tcard-win' : '',
        hinted && !selected ? 'tcard-hint' : '',
        onClick ? 'cursor-pointer' : '',
        className,
      ].join(' ')}
    >
      {tag && <span className="tcard-tag">{tag}</span>}
      <div className="tcard-face" style={{ color }}>
        {isTarokk ? (
          <>
            <div className="tcard-corner" style={{ fontSize: '17cqw' }}>
              <span>{label.length > 4 ? '' : '★'}</span>
            </div>
            <div className="tcard-center" style={{ fontSize: centerSize, paddingTop: 0 }}>
              {label}
            </div>
          </>
        ) : (
          <>
            <div className="tcard-corner">
              <span>{label}</span>
              <span className="sym">{symbol}</span>
            </div>
            <div className="tcard-center" style={{ fontSize: centerSize, opacity: 0.22 }}>
              {symbol}
            </div>
          </>
        )}
        {card.points > 1 && <div className="tcard-points">{card.points}</div>}
      </div>
      {!artFailed && (
        <>
          <img
            className="tcard-art"
            src={artOf(card)}
            alt=""
            draggable={false}
            onError={() => setArtFailed(true)}
          />
          {/* The court cards carry no letter in the painting */}
          {!isTarokk && card.rank !== '10' && <span className="tcard-rank" style={{ color }}>{label}</span>}
        </>
      )}
    </div>
  )
}

/** An empty place where a card will go. */
export function CardSlot({ width }: { width: string }) {
  return <div className="tcard-slot" style={{ width }} />
}
