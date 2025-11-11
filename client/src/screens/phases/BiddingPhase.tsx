import { motion } from 'framer-motion'
import { socketManager } from '@/services/socketManager'
import Hand from '@/components/Hand'
import PlayerAvatar from '@/components/PlayerAvatar'
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
  if (!bidType || bidType === 'pass') return 'Pass'
  return bidTypes.find((b) => b.value === bidType)?.label || bidType
}

export default function BiddingPhase({ gameState, playerPosition }: BiddingPhaseProps) {
  const isMyTurn = gameState.current_turn === playerPosition
  const currentPlayer = gameState.players[gameState.current_turn]
  const myPlayer = gameState.players[playerPosition]

  console.log('[BiddingPhase] Rendering...', {
    playerPosition,
    hasHand: !!myPlayer.hand,
    handSize: myPlayer.hand?.length || 0,
    hand: myPlayer.hand,
  })

  // Get valid bids - this would come from server in real implementation
  // For now, we allow all bid types that are higher than current highest bid
  const getValidBids = (): string[] => {
    if (gameState.bid_history.length === 0) {
      return bidTypes.map((b) => b.value)
    }

    const highestBid = gameState.bid_history
      .filter((b) => b.bid_type !== null && b.bid_type !== 'pass')
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
    <div className="w-full max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-6 shadow-2xl"
      >
        {/* Header */}
        <div className="text-center mb-4">
          <h2 className="text-2xl font-bold text-white mb-1">Bidding Phase</h2>
          <p className="text-slate-300 text-sm">
            {isMyTurn ? (
              <span className="text-yellow-400 font-semibold">Your turn to bid</span>
            ) : (
              <>
                Waiting for <span className="text-yellow-400 font-semibold">{currentPlayer.name}</span>
              </>
            )}
          </p>
        </div>

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
                      px-4 py-3 rounded-xl font-semibold text-white
                      transition-all duration-200
                      ${isValid ? getBidColor(bid.value) : 'bg-slate-700 text-slate-500 cursor-not-allowed'}
                      ${isValid ? 'shadow-lg' : ''}
                    `}
                  >
                    <div className="text-base">{bid.label}</div>
                    <div className="text-xs opacity-80 mt-0.5">{bid.description}</div>
                  </motion.button>
                )
              })}
            </div>

            {/* Pass Button */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handlePass}
              className="w-full px-4 py-2.5 bg-slate-600 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors"
            >
              Pass
            </motion.button>
          </div>
        )}

        {/* Waiting Message */}
        {!isMyTurn && (
          <div className="text-center py-4">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-4xl mb-2"
            >
              ⏳
            </motion.div>
            <p className="text-slate-400 text-sm">Waiting for {currentPlayer.name} to bid...</p>
          </div>
        )}
      </motion.div>

      {/* Player's Hand - Always visible during bidding */}
      {myPlayer.hand && myPlayer.hand.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-4 bg-slate-800/90 backdrop-blur-sm rounded-2xl px-4 py-2 shadow-2xl relative"
        >
          {/* Player Avatar in upper left corner */}
          <div className="absolute top-2 left-2 z-10">
            <PlayerAvatar
              player={myPlayer}
              isCurrentTurn={gameState.current_turn === playerPosition}
              position={playerPosition as 0 | 1 | 2 | 3}
              isLocalPlayer={true}
            />
          </div>

          <Hand
            cards={myPlayer.hand}
            layout="fan"
            size="md"
          />
        </motion.div>
      )}
    </div>
  )
}
