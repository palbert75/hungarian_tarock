import React from 'react'
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
  const trickWinnerAnimation = useGameStore((state) => state.trickWinnerAnimation)
  const lastTrickSnapshot = useGameStore((state) => state.lastTrickSnapshot)
  const [animateCollection, setAnimateCollection] = React.useState(false)

  // Wait before collecting cards so players can see the full trick
  React.useEffect(() => {
    if (!trickWinnerAnimation) {
      setAnimateCollection(false)
      return
    }

    setAnimateCollection(false)
    const timer = setTimeout(() => setAnimateCollection(true), 3000)
    return () => clearTimeout(timer)
  }, [trickWinnerAnimation])

  const myPlayer = gameState.players[playerPosition]
  const isMyTurn = gameState.current_turn === playerPosition

  // Convert absolute position to screen position (0=bottom, 1=left, 2=top, 3=right)
  const getRelativePosition = (absolutePosition: number): 0 | 1 | 2 | 3 => {
    return ((absolutePosition - playerPosition + 4) % 4) as 0 | 1 | 2 | 3
  }

  // Get target position for card collection animation based on winner's screen position
  const getWinnerTargetPosition = (winnerPosition: number) => {
    const screenPos = getRelativePosition(winnerPosition)
    switch (screenPos) {
      case 0: // bottom
        return { x: 0, y: 300 }
      case 1: // left
        return { x: -400, y: 0 }
      case 2: // top
        return { x: 0, y: -300 }
      case 3: // right
        return { x: 400, y: 0 }
    }
  }

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

  // Prefer live current_trick; if empty (e.g., server cleared quickly), fall back to snapshot
  const currentTrickCards = gameState.current_trick && gameState.current_trick.length > 0
    ? gameState.current_trick
    : lastTrickSnapshot

  return (
    <div className="w-full max-w-5xl mx-auto">
      {/* Trick Progress Bar */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel rounded-xl p-4 mb-4"
      >
        <div className="flex items-center justify-center gap-4 mb-3">
          <div className="text-slate-400 text-sm font-semibold uppercase tracking-wide">Trick Progress</div>
          <div className="text-xl font-bold text-white">
            {tricksCompleted} / {totalTricks}
          </div>
        </div>
        <div className="w-full bg-slate-950/70 rounded-full h-2 overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${(tricksCompleted / totalTricks) * 100}%` }}
            className="bg-gradient-to-r from-emerald-400 via-amber-300 to-blue-400 h-2 rounded-full"
            transition={{ duration: 0.5 }}
          />
        </div>

        {/* Player Tricks Won */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">
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
                  text-center p-2 rounded-lg border
                  ${isMe ? 'bg-blue-900/45 border-blue-400/70' : 'bg-slate-800/60 border-slate-600/40'}
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
        className="felt-panel rounded-xl p-4 md:p-8 mb-6"
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

        {/* Cards in Current Trick or Winner Animation */}
        <AnimatePresence mode="sync">
          {trickWinnerAnimation ? (
            // Winner animation: Show winning card highlighted, then collect cards
            <motion.div
              key="winner-animation"
              className="min-h-[240px]"
              initial={{ opacity: 1 }}
            >
              <div className="flex flex-wrap justify-center items-center gap-4 md:gap-6 relative">
                {trickWinnerAnimation.cards.map((trickCard, index) => {
                  const player = gameState.players[trickCard.player_position]
                  const playerName = player && player.name ? player.name : `Player ${trickCard.player_position + 1}`
                  const isWinningCard = index === trickWinnerAnimation.winning_card_index
                  const targetPos = getWinnerTargetPosition(trickWinnerAnimation.winner_position)

                  return (
                    <motion.div
                      key={`winner-${trickCard.player_position}-${index}`}
                      className="flex flex-col items-center gap-3"
                      initial={{ scale: 1, x: 0, y: 0 }}
                      animate={
                        animateCollection
                          ? {
                              // Collection phase: fly cards toward winner
                              scale: isWinningCard ? [1, 1.1, 0.8] : [1, 1, 0.8],
                              x: [0, 0, targetPos.x],
                              y: [0, 0, targetPos.y],
                              opacity: [1, 1, 0],
                            }
                          : {
                              // Preview phase: hold position, lightly highlight winner
                              scale: isWinningCard ? 1.08 : 1,
                              x: 0,
                              y: 0,
                              opacity: 1,
                            }
                      }
                      transition={
                        animateCollection
                          ? {
                              duration: 1.6,
                              times: [0, 0.35, 1],
                              ease: "easeInOut",
                            }
                          : {
                              duration: 0.3,
                              ease: "easeOut",
                            }
                      }
                      style={{
                        zIndex: isWinningCard ? 10 : 1
                      }}
                    >
                      <div className={`
                        ${isWinningCard ? 'ring-4 ring-yellow-400 rounded-xl shadow-2xl shadow-yellow-400/50' : ''}
                      `}>
                        <Card card={trickCard.card} size="lg" />
                      </div>
                      <div className={`
                        px-3 py-1 rounded-lg
                        ${isWinningCard ? 'bg-yellow-600' : 'bg-slate-700'}
                      `}>
                        <span className="text-white text-sm font-semibold">
                          {playerName}
                        </span>
                      </div>
                    </motion.div>
                  )
                })}
              </div>

              {/* Winner announcement overlay */}
              <motion.div
                initial={{ opacity: 0, scale: 0.8, y: 20 }}
                animate={
                  animateCollection
                    ? { opacity: [1, 0], scale: [1, 0.95] }
                    : { opacity: [0, 1], scale: [0.8, 1] }
                }
                transition={
                  animateCollection
                    ? { duration: 0.4, ease: "easeInOut" }
                    : { duration: 0.6, ease: "easeOut" }
                }
                className="absolute inset-0 flex items-center justify-center pointer-events-none z-30"
              >
                <div className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white px-6 md:px-8 py-4 rounded-xl shadow-2xl">
                  <div className="text-2xl md:text-3xl font-bold text-center">
                    {trickWinnerAnimation.winner_name} Wins
                  </div>
                  <div className="text-center text-yellow-100 mt-1">
                    Trick #{trickWinnerAnimation.trick_number}
                  </div>
                </div>
              </motion.div>
            </motion.div>
          ) : currentTrickCards && currentTrickCards.length > 0 ? (
            // Normal trick display
            <div key="normal-trick" className="flex flex-wrap justify-center items-center gap-4 md:gap-6 min-h-[180px]">
              {currentTrickCards.map((trickCard, index) => {
                const player = gameState.players[trickCard.player_position]
                const playerName = player && player.name ? player.name : `Player ${trickCard.player_position + 1}`
                return (
                  <motion.div
                    key={`${trickCard.player_position}-${index}`}
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ type: 'spring', stiffness: 260, damping: 20, delay: index * 0.05 }}
                    className="flex flex-col items-center gap-3"
                  >
                    <Card card={trickCard.card} size="lg" />
                    <div className="bg-slate-900/80 border border-slate-600/50 px-3 py-1 rounded-lg">
                      <span className="text-white text-sm font-semibold">
                        {playerName}
                      </span>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          ) : (
            // Waiting for first card
            <div key="waiting" className="flex items-center justify-center min-h-[180px]">
              <div className="text-center text-slate-400">
                <div className="mb-3 flex items-center justify-center">
                  <div className="w-12 h-12 border-4 border-slate-600 border-t-blue-400 rounded-full animate-spin" />
                </div>
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
        className="glass-panel rounded-xl p-4 md:p-6"
      >
          {isMyTurn ? (
            <>
              <div className="mb-4">
                <h3 className="text-white font-semibold text-center mb-2">Your Hand</h3>
                {validCards.length > 0 && validCards.length < myPlayer.hand.length && (
                  <p className="text-center text-slate-400 text-sm">
                    Only highlighted cards can be played
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
                    btn w-full px-6 py-4 rounded-xl font-semibold text-white text-lg
                    transition-all duration-200
                    ${
                      canPlayCard
                        ? 'btn-success'
                        : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                    }
                  `}
                >
                  {selectedCards.length === 0
                    ? 'Select a card to play'
                    : canPlayCard
                    ? 'Play Card'
                    : 'Invalid card selection'}
                </motion.button>
              </div>
            </>
          ) : (
            <>
              <div className="mb-4">
                <h3 className="text-white font-semibold text-center mb-2">Your Hand</h3>
                <p className="text-center text-slate-400 text-sm">
                  Waiting for {gameState.players[gameState.current_turn]?.name} to play...
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
