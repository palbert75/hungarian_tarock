import { motion } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import Hand from '@/components/Hand'
import type { GameState } from '@/types'

interface DiscardingPhaseProps {
  gameState: GameState
  playerPosition: number
}

export default function DiscardingPhase({ gameState, playerPosition }: DiscardingPhaseProps) {
  const selectedCards = useGameStore((state) => state.selectedCards)
  const toggleCardSelection = useGameStore((state) => state.toggleCardSelection)
  const clearSelectedCards = useGameStore((state) => state.clearSelectedCards)

  const myPlayer = gameState.players[playerPosition]
  const isMyTurn = gameState.current_turn === playerPosition

  // Calculate how many cards need to be discarded
  // Player should have 9 cards after discarding
  const targetHandSize = 9
  const currentHandSize = myPlayer.hand?.length || 0
  const cardsToDiscard = Math.max(0, currentHandSize - targetHandSize)
  const canConfirm = selectedCards.length === cardsToDiscard

  // Get valid cards to discard (would come from server in real implementation)
  // For now, we assume kings and honours cannot be discarded
  const getValidCards = (): string[] => {
    if (!myPlayer.hand) return []

    return myPlayer.hand
      .filter((card) => {
        // Cannot discard kings
        if (card.rank === 'K') return false
        // Cannot discard honours (I, XXI, skiz)
        // Note: server sends "skiz" in lowercase
        if (card.suit === 'tarokk' && ['I', 'XXI', 'skiz'].includes(card.rank)) return false
        return true
      })
      .map((card) => card.id)
  }

  const validCards = getValidCards()

  const handleConfirmDiscard = () => {
    if (canConfirm) {
      socketManager.discardCards(selectedCards)
      clearSelectedCards()
    }
  }

  // Count players who have already discarded
  const playersWhoDiscarded = gameState.players.filter((p) => p.has_discarded).length

  return (
    <div className="w-full max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-8 shadow-2xl"
      >
        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold text-white mb-2">Discarding Phase</h2>
          {isMyTurn ? (
            <>
              <p className="text-yellow-400 font-semibold mb-2">Your turn to discard</p>
              <p className="text-slate-300 text-sm">
                Select {cardsToDiscard} card{cardsToDiscard !== 1 ? 's' : ''} to discard
              </p>
            </>
          ) : (
            <p className="text-slate-300">
              Waiting for <span className="text-yellow-400 font-semibold">{gameState.players[gameState.current_turn]?.name}</span> to discard
            </p>
          )}
        </div>

        {/* Progress Indicator */}
        <div className="mb-6 bg-slate-700/50 rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-slate-300 text-sm font-semibold">Progress</span>
            <span className="text-slate-300 text-sm">{playersWhoDiscarded}/4 players</span>
          </div>
          <div className="w-full bg-slate-600 rounded-full h-2">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(playersWhoDiscarded / 4) * 100}%` }}
              className="bg-blue-500 h-2 rounded-full"
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>

        {isMyTurn ? (
          <>
            {/* Selection Counter */}
            <div className="mb-4 text-center">
              <div className="inline-block bg-slate-700 rounded-lg px-6 py-3">
                <span className="text-slate-300">Selected: </span>
                <span
                  className={`font-bold text-lg ${
                    selectedCards.length === cardsToDiscard
                      ? 'text-green-400'
                      : selectedCards.length > cardsToDiscard
                      ? 'text-red-400'
                      : 'text-yellow-400'
                  }`}
                >
                  {selectedCards.length}
                </span>
                <span className="text-slate-300"> / {cardsToDiscard}</span>
              </div>
            </div>

            {/* Hand */}
            {myPlayer.hand && myPlayer.hand.length > 0 && (
              <Hand
                cards={myPlayer.hand}
                selectedCards={selectedCards}
                validCards={validCards}
                onCardClick={toggleCardSelection}
                layout="fan"
                size="md"
              />
            )}

            {/* Info about invalid cards */}
            <div className="mt-4 text-center text-slate-400 text-sm">
              <p>⚠️ Cannot discard Kings or Honours (I, XXI, Skíz)</p>
            </div>

            {/* Confirm Button */}
            <div className="mt-6">
              <motion.button
                whileHover={canConfirm ? { scale: 1.02 } : undefined}
                whileTap={canConfirm ? { scale: 0.98 } : undefined}
                onClick={handleConfirmDiscard}
                disabled={!canConfirm}
                className={`
                  w-full px-6 py-4 rounded-xl font-semibold text-white text-lg
                  transition-all duration-200
                  ${
                    canConfirm
                      ? 'bg-green-600 hover:bg-green-700 shadow-lg'
                      : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  }
                `}
              >
                {canConfirm ? '✓ Confirm Discard' : `Select ${cardsToDiscard - selectedCards.length} more card${cardsToDiscard - selectedCards.length !== 1 ? 's' : ''}`}
              </motion.button>
            </div>
          </>
        ) : (
          /* Waiting Message */
          <>
            <div className="text-center py-4">
              <motion.div
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="text-4xl mb-2"
              >
                ⏳
              </motion.div>
              <p className="text-slate-400 text-sm">
                Waiting for {gameState.players[gameState.current_turn]?.name} to discard...
              </p>
            </div>

            {/* Show player's hand (view-only when not their turn) */}
            {myPlayer.hand && myPlayer.hand.length > 0 && (
              <div className="mt-4">
                <Hand
                  cards={myPlayer.hand}
                  layout="fan"
                  size="md"
                />
              </div>
            )}
          </>
        )}
      </motion.div>
    </div>
  )
}
