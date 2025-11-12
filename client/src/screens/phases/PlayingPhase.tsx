import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import Hand from '@/components/Hand'
import Card from '@/components/Card'
import type { GameState } from '@/types'

interface PlayingPhaseProps {
  gameState: GameState
  playerPosition: number
}

export default function PlayingPhase({ gameState, playerPosition }: PlayingPhaseProps) {
  const selectedCards = useGameStore((state) => state.selectedCards)
  const toggleCardSelection = useGameStore((state) => state.toggleCardSelection)
  const clearSelectedCards = useGameStore((state) => state.clearSelectedCards)

  const myPlayer = gameState.players[playerPosition]
  const isMyTurn = gameState.current_turn === playerPosition

  // Get valid cards to play (would come from server in real implementation)
  // If server doesn't provide valid cards, allow all cards in hand
  const validCards = gameState.valid_cards && gameState.valid_cards.length > 0
    ? gameState.valid_cards
    : (myPlayer.hand?.map(card => card.id) || [])

  const handlePlayCard = () => {
    if (selectedCards.length === 1 && validCards.includes(selectedCards[0])) {
      socketManager.playCard(selectedCards[0])
      clearSelectedCards()
    }
  }

  const canPlayCard = selectedCards.length === 1 && validCards.includes(selectedCards[0])

  // Calculate tricks won (trick_number is 0-indexed, shows completed tricks)
  const tricksCompleted = gameState.trick_number || 0
  const totalTricks = 9 // Hungarian Tarokk has 9 tricks (36 cards / 4 players = 9 tricks each)

  // Get tricks won by each player (server sends tricks_won_count)
  const getPlayerTricksWon = (player: any) => {
    return player.tricks_won_count || 0
  }

  return (
    <div className="w-full max-w-5xl mx-auto">
      {/* Trick Progress Bar */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-4 mb-4 shadow-xl"
      >
        <div className="flex items-center justify-center gap-4 mb-3">
          <div className="text-slate-400 text-sm">Trick Progress</div>
          <div className="text-xl font-bold text-white">
            {tricksCompleted} / {totalTricks}
          </div>
        </div>
        <div className="w-full bg-slate-700 rounded-full h-3">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(tricksCompleted / totalTricks) * 100}%` }}
            className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full"
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Player Tricks Won */}
        <div className="grid grid-cols-4 gap-2 mt-4">
          {gameState.players.map((player, idx) => {
            const tricksWon = getPlayerTricksWon(player)
            const isMe = idx === playerPosition
            const isDeclarer = idx === gameState.declarer_position
            const isPartner = gameState.partner_revealed && idx === gameState.partner_position
            const isDealer = idx === gameState.dealer_position

            return (
              <div
                key={idx}
                className={`
                  text-center p-2 rounded-lg
                  ${isMe ? 'bg-blue-900/50 border-2 border-blue-500' : 'bg-slate-700/50'}
                `}
              >
                <div className="text-xs text-slate-400 truncate">
                  {player.name}
                  {isDealer && ' 🃏'}
                  {isDeclarer && ' 👑'}
                  {isPartner && ' 🤝'}
                </div>
                <div className="text-lg font-bold text-white">
                  {tricksWon} tricks
                </div>
              </div>
            )
          })}
        </div>
      </motion.div>

      {/* Current Trick Display */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-8 mb-6 shadow-2xl"
      >
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-white mb-2">
            Trick #{gameState.trick_number || 0}
          </h2>
          <p className="text-slate-300">
            {isMyTurn ? (
              <span className="text-yellow-400 font-semibold">Your turn to play</span>
            ) : (
              <>
                Waiting for{' '}
                <span className="text-yellow-400 font-semibold">
                  {gameState.players[gameState.current_turn]?.name}
                </span>
              </>
            )}
          </p>
        </div>

        {/* Cards in Current Trick */}
        <AnimatePresence mode="popLayout">
          {gameState.current_trick && gameState.current_trick.length > 0 ? (
            <div className="flex justify-center items-center gap-6 min-h-[180px]">
              {gameState.current_trick.map((trickCard, index) => {
                const player = gameState.players[trickCard.player_position]
                const playerName = player && player.name ? player.name : `Player ${trickCard.player_position + 1}`
                return (
                  <motion.div
                    key={`${trickCard.player_position}-${index}`}
                    initial={{ scale: 0, rotate: -180, opacity: 0 }}
                    animate={{ scale: 1, rotate: 0, opacity: 1 }}
                    exit={{ scale: 0, rotate: 180, opacity: 0 }}
                    transition={{
                      type: 'spring',
                      stiffness: 260,
                      damping: 20,
                      delay: index * 0.1,
                    }}
                    className="flex flex-col items-center gap-3"
                  >
                    <Card card={trickCard.card} size="lg" />
                    <div className="bg-slate-700 px-3 py-1 rounded-lg">
                      <span className="text-white text-sm font-semibold">
                        {playerName}
                      </span>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          ) : (
            <div className="flex items-center justify-center min-h-[180px]">
              <div className="text-center text-slate-400">
                <motion.div
                  animate={{ scale: [1, 1.1, 1] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="text-6xl mb-3"
                >
                  🎴
                </motion.div>
                <p>Waiting for first card...</p>
              </div>
            </div>
          )}
        </AnimatePresence>

        {/* Leader indicator */}
        {gameState.current_trick && gameState.current_trick.length > 0 && (() => {
          const leaderPosition = gameState.current_trick[0].player_position
          const leader = gameState.players[leaderPosition]
          const leaderName = leader && leader.name ? leader.name : `Player ${leaderPosition + 1}`
          return (
            <div className="text-center mt-4 text-slate-400 text-sm">
              <span className="text-yellow-400 font-semibold">
                {leaderName}
              </span>{' '}
              leads this trick
            </div>
          )
        })()}
      </motion.div>

      {/* Player's Hand - Always visible */}
      {myPlayer.hand && myPlayer.hand.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-6 shadow-2xl"
        >
          {isMyTurn ? (
            <>
              <div className="mb-4">
                <h3 className="text-white font-semibold text-center mb-2">Your Hand</h3>
                {validCards.length > 0 && validCards.length < myPlayer.hand.length && (
                  <p className="text-center text-slate-400 text-sm">
                    💡 Only highlighted cards can be played
                  </p>
                )}
              </div>

              <Hand
                cards={myPlayer.hand}
                selectedCards={selectedCards}
                validCards={validCards}
                onCardClick={toggleCardSelection}
                layout="fan"
                size="md"
              />

              {/* Play Card Button */}
              <div className="mt-6">
                <motion.button
                  whileHover={canPlayCard ? { scale: 1.02 } : undefined}
                  whileTap={canPlayCard ? { scale: 0.98 } : undefined}
                  onClick={handlePlayCard}
                  disabled={!canPlayCard}
                  className={`
                    w-full px-6 py-4 rounded-xl font-semibold text-white text-lg
                    transition-all duration-200
                    ${
                      canPlayCard
                        ? 'bg-green-600 hover:bg-green-700 shadow-lg'
                        : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                    }
                  `}
                >
                  {selectedCards.length === 0
                    ? 'Select a card to play'
                    : canPlayCard
                    ? '✓ Play Card'
                    : 'Invalid card selection'}
                </motion.button>
              </div>
            </>
          ) : (
            <>
              <div className="mb-4">
                <h3 className="text-white font-semibold text-center mb-2">Your Hand</h3>
                <p className="text-center text-slate-400 text-sm">
                  ⏳ Waiting for {gameState.players[gameState.current_turn]?.name} to play...
                </p>
              </div>

              {/* Show hand but not clickable when not your turn */}
              <Hand
                cards={myPlayer.hand}
                layout="fan"
                size="md"
              />
            </>
          )}
        </motion.div>
      )}
    </div>
  )
}
