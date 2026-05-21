import { motion } from 'framer-motion'
import type { Card as CardType } from '@/types'

interface CardProps {
  card: CardType
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  selectable?: boolean
  selected?: boolean
  disabled?: boolean
  faceDown?: boolean
  onClick?: () => void
}

const sizeClasses = {
  xs: 'w-12 h-16 text-xs',
  sm: 'w-16 h-24 text-sm',
  md: 'w-20 h-32 text-base',
  lg: 'w-24 h-36 text-lg',
  xl: 'w-32 h-48 text-xl',
}

const getSuitColor = (suit: string): string => {
  switch (suit) {
    case 'hearts':
    case 'diamonds':
      return 'text-red-600'
    case 'clubs':
    case 'spades':
      return 'text-slate-900'
    case 'tarokk':
      return 'text-purple-800'
    default:
      return 'text-slate-900'
  }
}

const getSuitSymbol = (suit: string): string => {
  switch (suit) {
    case 'hearts':
      return '♥'
    case 'diamonds':
      return '♦'
    case 'clubs':
      return '♣'
    case 'spades':
      return '♠'
    case 'tarokk':
      return '★'
    default:
      return ''
  }
}

const getCardDisplayName = (card: CardType): string => {
  // For tarokk cards, show the rank number (I, II, III, ... XXI, Škis)
  if (card.suit === 'tarokk') {
    return card.rank
  }

  // For suit cards, show rank
  return card.rank
}

export default function Card({
  card,
  size = 'md',
  selectable = false,
  selected = false,
  disabled = false,
  faceDown = false,
  onClick,
}: CardProps) {
  const isClickable = selectable && !disabled && onClick
  const suitColor = getSuitColor(card.suit)
  const suitSymbol = getSuitSymbol(card.suit)
  const displayName = getCardDisplayName(card)
  const isTarokk = card.suit === 'tarokk'
  const rankSize = size === 'xs' || size === 'sm' ? 'text-[0.68rem]' : 'text-sm'
  const suitSize = size === 'xs' || size === 'sm' ? 'text-base' : 'text-xl'
  const centerSize = size === 'xl' ? '4rem' : size === 'lg' ? '3rem' : size === 'sm' ? '1.65rem' : size === 'xs' ? '1.35rem' : '2.2rem'

  return (
    <motion.div
      whileHover={isClickable ? { y: -10, scale: 1.045 } : undefined}
      whileTap={isClickable ? { scale: 0.95 } : undefined}
      animate={selected ? { y: -16, scale: 1.04 } : { y: 0, scale: 1 }}
      onClick={isClickable ? onClick : undefined}
      className={`
        ${sizeClasses[size]}
        playing-card relative
        transition-all duration-200
        ${isClickable ? 'cursor-pointer' : ''}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        ${selected ? 'ring-4 ring-yellow-300 ring-offset-2 ring-offset-emerald-950' : ''}
      `}
    >
      {faceDown ? (
        // Card back design
        <div className="card-back w-full h-full rounded-xl border border-red-950/60 flex items-center justify-center overflow-hidden">
          <div className="w-3/4 h-3/4 rounded-lg border border-yellow-200/25 flex items-center justify-center">
            <div className="text-yellow-100/70 font-display text-2xl">T</div>
          </div>
        </div>
      ) : (
        // Card front design
        <div
          className={`
            card-face w-full h-full rounded-xl border
            ${isTarokk ? 'border-violet-500/70' : 'border-slate-300'}
            flex flex-col p-1.5 overflow-hidden
            ${disabled ? 'grayscale' : ''}
          `}
        >
          {/* Top rank and suit */}
          <div className={`flex flex-col items-start ${suitColor} font-black leading-none`}>
            <div className={`${rankSize} max-w-full truncate`}>{displayName}</div>
            <div className={suitSize}>{suitSymbol}</div>
          </div>

          {/* Center suit symbol (larger) */}
          <div className="flex-1 flex items-center justify-center min-h-0 relative">
            {isTarokk && (
              <div className="absolute inset-x-2 top-1/2 h-px bg-violet-200/60" />
            )}
            <div className={`${suitColor} opacity-25 drop-shadow-sm`}>
              <div style={{ fontSize: centerSize, lineHeight: 1 }}>
                {suitSymbol}
              </div>
            </div>
          </div>

          {/* Bottom rank and suit (rotated 180°) */}
          <div className={`flex flex-col items-start self-end ${suitColor} font-black leading-none rotate-180`}>
            <div className={`${rankSize} max-w-full truncate`}>{displayName}</div>
            <div className={suitSize}>{suitSymbol}</div>
          </div>

          {/* Point value indicator (if non-zero) */}
          {card.points > 0 && (
            <div className="absolute bottom-1 right-1 bg-amber-500 text-slate-950 text-[0.65rem] font-black rounded-full w-5 h-5 flex items-center justify-center shadow-md">
              {card.points}
            </div>
          )}

          {/* Disabled overlay */}
          {disabled && (
            <div className="absolute inset-0 bg-slate-900/20 rounded-xl flex items-center justify-center">
              <div className="px-2 py-1 rounded-md bg-slate-950/70 text-white text-[0.65rem] font-bold">
                Locked
              </div>
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}
