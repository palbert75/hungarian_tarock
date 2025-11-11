import { motion } from 'framer-motion'
import { useState } from 'react'
import { socketManager } from '@/services/socketManager'
import Hand from '@/components/Hand'
import PlayerAvatar from '@/components/PlayerAvatar'
import type { GameState } from '@/types'

interface PartnerCallPhaseProps {
  gameState: GameState
  playerPosition: number
}

// Tarokk cards that can be called as partner (typically higher tarokks)
const callableTarokks = [
  { value: 'XX', label: 'XX', description: 'Tarokk 20' },
  { value: 'XIX', label: 'XIX', description: 'Tarokk 19' },
  { value: 'XVIII', label: 'XVIII', description: 'Tarokk 18' },
  { value: 'XVII', label: 'XVII', description: 'Tarokk 17' },
  { value: 'XVI', label: 'XVI', description: 'Tarokk 16' },
  { value: 'XV', label: 'XV', description: 'Tarokk 15' },
  { value: 'XIV', label: 'XIV', description: 'Tarokk 14' },
  { value: 'XIII', label: 'XIII', description: 'Tarokk 13' },
  { value: 'XII', label: 'XII', description: 'Tarokk 12' },
  { value: 'XI', label: 'XI', description: 'Tarokk 11' },
  { value: 'X', label: 'X', description: 'Tarokk 10' },
]

export default function PartnerCallPhase({ gameState, playerPosition }: PartnerCallPhaseProps) {
  const [selectedTarokk, setSelectedTarokk] = useState<string | null>(null)

  const myPlayer = gameState.players[playerPosition]
  const isIDeclarer = myPlayer.is_declarer
  const declarer = gameState.players.find((p) => p.is_declarer)

  const handleCallPartner = () => {
    if (selectedTarokk) {
      socketManager.callPartner(selectedTarokk)
      setSelectedTarokk(null)
    }
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
          <div className="text-6xl mb-4">👑</div>
          <h2 className="text-3xl font-bold text-white mb-2">Call Your Partner</h2>
          {isIDeclarer ? (
            <p className="text-yellow-400 font-semibold">
              Choose a tarokk to call as your partner
            </p>
          ) : (
            <p className="text-slate-300">
              Waiting for <span className="text-yellow-400 font-semibold">{declarer?.name}</span> to
              call partner...
            </p>
          )}
        </div>

        {isIDeclarer ? (
          <>
            {/* Info Box */}
            <div className="mb-6 bg-blue-900/30 border border-blue-500/50 rounded-xl p-4">
              <h3 className="text-blue-400 font-semibold mb-2 text-sm">How it works:</h3>
              <ul className="text-slate-300 text-sm space-y-1">
                <li>• Select a tarokk card you don't have</li>
                <li>• The player holding it becomes your partner</li>
                <li>• They remain secret until they play the called card</li>
                <li>• You play as a team of 2 against the other 2</li>
              </ul>
            </div>

            {/* Tarokk Selection Grid */}
            <div className="mb-6">
              <h3 className="text-white font-semibold mb-3 text-center">
                Select a Tarokk to Call
              </h3>
              <div className="grid grid-cols-4 gap-2">
                {callableTarokks.map((tarokk) => {
                  const isSelected = selectedTarokk === tarokk.value
                  // Check if player has this card (would be invalid to call)
                  const iHaveThisCard = myPlayer.hand?.some(
                    (card) => card.suit === 'tarokk' && card.rank === tarokk.value
                  )

                  return (
                    <motion.button
                      key={tarokk.value}
                      whileHover={!iHaveThisCard ? { scale: 1.05 } : undefined}
                      whileTap={!iHaveThisCard ? { scale: 0.95 } : undefined}
                      onClick={() => !iHaveThisCard && setSelectedTarokk(tarokk.value)}
                      disabled={iHaveThisCard}
                      className={`
                        px-3 py-4 rounded-lg font-bold text-lg
                        transition-all duration-200
                        ${
                          isSelected
                            ? 'bg-gold text-white ring-4 ring-yellow-400 scale-105'
                            : iHaveThisCard
                            ? 'bg-slate-700 text-slate-500 cursor-not-allowed opacity-50'
                            : 'bg-slate-700 text-gold hover:bg-slate-600'
                        }
                      `}
                    >
                      {tarokk.label}
                    </motion.button>
                  )
                })}
              </div>
              <p className="text-slate-400 text-xs text-center mt-3">
                Cards you own are disabled
              </p>
            </div>

            {/* Selected Card Display */}
            {selectedTarokk && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-6 bg-slate-700/50 rounded-xl p-4 text-center"
              >
                <p className="text-slate-300 text-sm mb-2">You will call:</p>
                <div className="text-3xl font-bold text-gold">Tarokk {selectedTarokk}</div>
              </motion.div>
            )}

            {/* Confirm Button */}
            <motion.button
              whileHover={selectedTarokk ? { scale: 1.02 } : undefined}
              whileTap={selectedTarokk ? { scale: 0.98 } : undefined}
              onClick={handleCallPartner}
              disabled={!selectedTarokk}
              className={`
                w-full px-6 py-4 rounded-xl font-semibold text-white text-lg
                transition-all duration-200
                ${
                  selectedTarokk
                    ? 'bg-green-600 hover:bg-green-700 shadow-lg'
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                }
              `}
            >
              {selectedTarokk ? '✓ Confirm Partner Call' : 'Select a Tarokk First'}
            </motion.button>
          </>
        ) : (
          /* Waiting Screen for Non-Declarers */
          <div className="text-center py-6">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-4xl mb-3"
            >
              ⏳
            </motion.div>
            <p className="text-slate-400 mb-3 text-sm">
              {declarer?.name} is selecting their partner...
            </p>
            <div className="bg-slate-700/50 rounded-xl p-4 max-w-md mx-auto">
              <p className="text-slate-300 text-xs">
                The partner will remain secret until they play the called card during the game.
              </p>
            </div>
          </div>
        )}

        {/* Already Called Info */}
        {gameState.called_card && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 bg-green-900/30 border border-green-500/50 rounded-xl p-4 text-center"
          >
            <div className="text-green-400 font-semibold mb-1">Partner Called!</div>
            <div className="text-white text-xl font-bold">Tarokk {gameState.called_card}</div>
            <div className="text-slate-400 text-sm mt-2">
              The partner will be revealed when this card is played
            </div>
          </motion.div>
        )}
      </motion.div>

      {/* Player's Hand - Always visible */}
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
