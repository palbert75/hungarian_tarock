import { motion } from 'framer-motion'
import Card from './Card'
import type { Card as CardType } from '@/types'

interface HandProps {
  cards: CardType[]
  selectedCards?: string[]
  validCards?: string[]
  onCardClick?: (cardId: string) => void
  layout?: 'fan' | 'straight'
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
}

export default function Hand({
  cards,
  selectedCards = [],
  validCards,
  onCardClick,
  layout = 'fan',
  size = 'md',
}: HandProps) {
  const cardCount = cards.length

  // Calculate fan spread based on number of cards
  const maxSpread = 40 // Maximum rotation in degrees
  const spreadAngle = cardCount > 1 ? Math.min(maxSpread, cardCount * 3) : 0
  const angleStep = cardCount > 1 ? spreadAngle / (cardCount - 1) : 0
  const startAngle = -spreadAngle / 2

  // Calculate card overlap
  const overlapPercent = layout === 'fan' ? 70 : 20 // 70% overlap for fan, 20% for straight

  const getCardStyle = (index: number) => {
    if (layout === 'straight') {
      return {
        transform: 'rotate(0deg)',
        zIndex: index,
      }
    }

    // Fan layout
    const angle = startAngle + angleStep * index
    const verticalOffset = Math.abs(angle) * 0.5 // Cards in center are slightly higher

    return {
      transform: `rotate(${angle}deg) translateY(${verticalOffset}px)`,
      zIndex: index,
    }
  }

  const isCardValid = (cardId: string): boolean => {
    // If validCards is not provided, all cards are valid
    if (!validCards) return true
    return validCards.includes(cardId)
  }

  const isCardDisabled = (cardId: string): boolean => {
    // If validCards is provided and card is not in it, it's disabled
    if (validCards && !validCards.includes(cardId)) return true
    return false
  }

  // Calculate container width based on overlap
  const cardWidths = {
    xs: 48, // 12 * 4px (w-12)
    sm: 64, // 16 * 4px (w-16)
    md: 80, // 20 * 4px (w-20)
    lg: 96, // 24 * 4px (w-24)
    xl: 128, // 32 * 4px (w-32)
  }
  const cardWidth = cardWidths[size]
  const overlapWidth = cardWidth * (overlapPercent / 100)
  const totalWidth = cardCount > 0 ? cardWidth + (cardCount - 1) * overlapWidth : 0

  return (
    <div className="flex items-center justify-center py-8">
      <div
        className="relative flex items-end justify-center"
        style={{
          width: `${totalWidth}px`,
          height: layout === 'fan' ? '200px' : 'auto',
        }}
      >
        {cards.map((card, index) => {
          const isSelected = selectedCards.includes(card.id)
          const isDisabled = isCardDisabled(card.id)

          return (
            <motion.div
              key={card.id}
              className="absolute"
              style={{
                ...getCardStyle(index),
                left: `${index * overlapWidth}px`,
                transformOrigin: 'bottom center',
              }}
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.3 }}
            >
              <Card
                card={card}
                size={size}
                selectable={!!onCardClick}
                selected={isSelected}
                disabled={isDisabled}
                onClick={() => onCardClick?.(card.id)}
              />
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
