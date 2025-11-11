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

  return (
    <motion.div
      whileHover={isClickable ? { y: -8, scale: 1.05 } : undefined}
      whileTap={isClickable ? { scale: 0.95 } : undefined}
      animate={selected ? { y: -12 } : { y: 0 }}
      onClick={isClickable ? onClick : undefined}
      className={`
        ${sizeClasses[size]}
        relative rounded-lg shadow-lg
        transition-all duration-200
        ${isClickable ? 'cursor-pointer' : ''}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
        ${selected ? 'ring-4 ring-blue-500 ring-offset-2' : ''}
      `}
    >
      {faceDown ? (
        // Card back design
        <div className="w-full h-full bg-gradient-to-br from-slate-700 via-slate-800 to-slate-900 rounded-lg border-2 border-slate-600 flex items-center justify-center">
          <div className="text-4xl opacity-30">🎴</div>
        </div>
      ) : (
        // Card front design
        <div
          className={`
            w-full h-full bg-white rounded-lg border-2
            ${card.suit === 'tarokk' ? 'border-purple-700' : 'border-slate-300'}
            flex flex-col p-1.5
            ${disabled ? 'bg-slate-100' : ''}
          `}
        >
          {/* Top rank and suit */}
          <div className={`flex flex-col items-center ${suitColor} font-bold leading-none`}>
            <div className="text-sm">{displayName}</div>
            <div className="text-xl">{suitSymbol}</div>
          </div>

          {/* Center suit symbol (larger) */}
          <div className="flex-1 flex items-center justify-center min-h-0">
            <div className={`${suitColor} opacity-20`}>
              <div style={{ fontSize: size === 'xl' ? '4rem' : size === 'lg' ? '3rem' : '2rem' }}>
                {suitSymbol}
              </div>
            </div>
          </div>

          {/* Bottom rank and suit (rotated 180°) */}
          <div className={`flex flex-col items-center ${suitColor} font-bold leading-none rotate-180`}>
            <div className="text-sm">{displayName}</div>
            <div className="text-xl">{suitSymbol}</div>
          </div>

          {/* Point value indicator (if non-zero) */}
          {card.points > 0 && (
            <div className="absolute bottom-1 right-1 bg-gold text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center">
              {card.points}
            </div>
          )}

          {/* Disabled overlay */}
          {disabled && (
            <div className="absolute inset-0 bg-slate-500/20 rounded-lg flex items-center justify-center">
              <div className="text-4xl opacity-50">🚫</div>
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}
