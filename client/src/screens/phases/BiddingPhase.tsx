import { motion } from 'framer-motion'
import { socketManager } from '@/services/socketManager'
import type { Bid, GameState } from '@/types'

interface BiddingPhaseProps {
  gameState: GameState
  playerPosition: number
}

const bidTypes = [
  { value: 'three', label: 'Three', description: '3 from talon' },
  { value: 'two', label: 'Two', description: '2 from talon' },
  { value: 'one', label: 'One', description: '1 from talon' },
  { value: 'solo', label: 'Solo', description: 'No talon' },
]

const getBidColor = (bidType: string): string => {
  switch (bidType) {
    case 'three':
      return 'bg-blue-600 hover:bg-blue-700'
    case 'two':
      return 'bg-purple-600 hover:bg-purple-700'
    case 'one':
      return 'bg-orange-600 hover:bg-orange-700'
    case 'solo':
      return 'bg-red-600 hover:bg-red-700'
    default:
      return 'bg-slate-600'
  }
}

const getBidDisplayName = (bidType: string | null): string => {
  if (!bidType) return 'Pass'
  return bidTypes.find((b) => b.value === bidType)?.label || bidType
}

export default function BiddingPhase({ gameState, playerPosition }: BiddingPhaseProps) {
  const isMyTurn = gameState.current_turn === playerPosition
  const currentPlayer = gameState.players[gameState.current_turn]

  // Get valid bids - this would come from server in real implementation
  // For now, we allow all bid types that are higher than current highest bid
  const getValidBids = (): string[] => {
    if (gameState.bid_history.length === 0) {
      return bidTypes.map((b) => b.value)
    }

    const highestBid = gameState.bid_history
      .filter((b) => b.bid_type !== null)
      .slice(-1)[0]

    if (!highestBid || !highestBid.bid_type) {
      return bidTypes.map((b) => b.value)
    }

    const bidOrder = ['three', 'two', 'one', 'solo']
    const highestIndex = bidOrder.indexOf(highestBid.bid_type)
    return bidOrder.slice(highestIndex + 1)
  }

  const validBids = getValidBids()

  const handleBid = (bidType: string) => {
    socketManager.placeBid(bidType)
  }

  const handlePass = () => {
    socketManager.pass()
  }

  return (
    <div className="w-full max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-8 shadow-2xl"
      >
        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold text-white mb-2">Bidding Phase</h2>
          <p className="text-slate-300">
            {isMyTurn ? (
              <span className="text-yellow-400 font-semibold">Your turn to bid</span>
            ) : (
              <>
                Waiting for <span className="text-yellow-400 font-semibold">{currentPlayer.name}</span>
              </>
            )}
          </p>
        </div>

        {/* Bid History */}
        {gameState.bid_history.length > 0 && (
          <div className="mb-6 bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3 text-sm">Bid History</h3>
            <div className="space-y-2">
              {gameState.bid_history.map((bid: Bid, index: number) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-slate-300">
                    {gameState.players[bid.player_position]?.name}
                  </span>
                  <span
                    className={`
                      font-semibold px-3 py-1 rounded-lg
                      ${
                        bid.bid_type
                          ? getBidColor(bid.bid_type) + ' text-white'
                          : 'bg-slate-600 text-slate-300'
                      }
                    `}
                  >
                    {getBidDisplayName(bid.bid_type)}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {/* Bid Buttons */}
        {isMyTurn && (
          <div className="space-y-4">
            {/* Bid Type Grid */}
            <div className="grid grid-cols-2 gap-3">
              {bidTypes.map((bid) => {
                const isValid = validBids.includes(bid.value)
                return (
                  <motion.button
                    key={bid.value}
                    whileHover={isValid ? { scale: 1.02 } : undefined}
                    whileTap={isValid ? { scale: 0.98 } : undefined}
                    onClick={() => isValid && handleBid(bid.value)}
                    disabled={!isValid}
                    className={`
                      px-6 py-4 rounded-xl font-semibold text-white
                      transition-all duration-200
                      ${isValid ? getBidColor(bid.value) : 'bg-slate-700 text-slate-500 cursor-not-allowed'}
                      ${isValid ? 'shadow-lg' : ''}
                    `}
                  >
                    <div className="text-lg">{bid.label}</div>
                    <div className="text-xs opacity-80 mt-1">{bid.description}</div>
                  </motion.button>
                )
              })}
            </div>

            {/* Pass Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handlePass}
              className="w-full px-6 py-3 bg-slate-600 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors"
            >
              Pass
            </motion.button>
          </div>
        )}

        {/* Waiting Message */}
        {!isMyTurn && (
          <div className="text-center py-8">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-6xl mb-4"
            >
              ⏳
            </motion.div>
            <p className="text-slate-400">Waiting for {currentPlayer.name} to bid...</p>
          </div>
        )}
      </motion.div>
    </div>
  )
}
