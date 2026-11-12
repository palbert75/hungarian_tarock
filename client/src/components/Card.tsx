import { useState } from 'react'
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
  className?: string
}

const colorOf = (suit: string): string =>
  suit === 'hearts' || suit === 'diamonds' ? '#b91c1c' : suit === 'tarokk' ? '#3730a3' : '#111827'

/** Painted card faces live in public/cards (made by scripts/slice-cards.py). */
const artOf = (card: CardType): string =>
  `/cards/${card.suit}-${card.suit === 'tarokk' && card.rank.toLowerCase() === 'skiz' ? 'skiz' : card.rank}.webp`

/** A playing card. The painted face is used when it loads; the drawn one is the fallback. */
export default function Card({ card, width, selected, dimmed, winner, hinted, tag, onClick, className = '' }: CardProps) {
  const { t } = useTranslation()
  const [artFailed, setArtFailed] = useState(false)
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
      onClick={onClick}
      style={width ? { width } : undefined}
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
