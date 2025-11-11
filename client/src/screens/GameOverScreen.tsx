import { motion } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import type { GameState } from '@/types'

interface GameOverScreenProps {
  gameState: GameState
  playerPosition: number
}

export default function GameOverScreen({ gameState, playerPosition }: GameOverScreenProps) {
  const myPlayer = gameState.players[playerPosition]

  // Calculate team scores (server already calculated total_points per player)
  const declarerTeamScore = gameState.players
    .filter((p, idx) => idx === gameState.declarer_position || (gameState.partner_revealed && idx === gameState.partner_position))
    .reduce((sum, p) => sum + p.total_points, 0)

  const opponentTeamScore = gameState.players
    .filter((p, idx) => idx !== gameState.declarer_position && !(gameState.partner_revealed && idx === gameState.partner_position))
    .reduce((sum, p) => sum + p.total_points, 0)

  const declarerWon = declarerTeamScore >= 48 // Need 48+ points to win

  // Am I on the winning team?
  const amIWinner = myPlayer.is_declarer || myPlayer.is_partner ? declarerWon : !declarerWon

  // Get declarer and partner
  const declarer = gameState.players.find((p) => p.is_declarer)
  const partner = gameState.players.find((p) => p.is_partner)

  // Get player stats
  const playerStats = gameState.players.map((player, idx) => ({
    name: player.name,
    cardPoints: player.total_points, // Server already calculated this
    tricksWon: player.tricks_won_count || 0,
    isMe: idx === playerPosition,
    isDeclarer: player.is_declarer,
    isPartner: player.is_partner,
  }))

  const handlePlayAgain = () => {
    // Would need server support to restart game in same room
    const playerName = useGameStore.getState().playerName
    socketManager.leaveRoom()
    useGameStore.persist.clearStorage()
    if (playerName) {
      useGameStore.getState().setPlayerInfo('', playerName)
    }
  }

  const handleReturnToLobby = () => {
    const playerName = useGameStore.getState().playerName
    socketManager.leaveRoom()
    useGameStore.persist.clearStorage()
    if (playerName) {
      useGameStore.getState().setPlayerInfo('', playerName)
    }
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="w-full max-w-3xl px-6"
      >
        {/* Result Header */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="text-center mb-8"
        >
          <div className="text-8xl mb-4">
            {amIWinner ? '🎉' : '😔'}
          </div>
          <h1 className="text-5xl font-bold text-white mb-2">
            {amIWinner ? 'Victory!' : 'Game Over'}
          </h1>
          <p className="text-2xl text-slate-300">
            {declarerWon ? 'Declarer Team Wins!' : 'Opponent Team Wins!'}
          </p>
        </motion.div>

        {/* Team Scores */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="grid grid-cols-2 gap-4 mb-8"
        >
          {/* Declarer Team */}
          <div className={`bg-slate-800 rounded-2xl p-6 border-2 ${declarerWon ? 'border-green-500' : 'border-slate-700'}`}>
            <div className="text-center">
              <div className="text-sm text-slate-400 mb-2">Declarer Team</div>
              <div className="text-4xl font-bold text-blue-400 mb-3">{declarerTeamScore}</div>
              <div className="space-y-2">
                {declarer && (
                  <div className="bg-slate-700/50 rounded-lg px-3 py-2">
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-gold">👑</span>
                      <span className="text-white font-semibold">{declarer.name}</span>
                    </div>
                  </div>
                )}
                {partner && (
                  <div className="bg-slate-700/50 rounded-lg px-3 py-2">
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-blue-400">🤝</span>
                      <span className="text-white font-semibold">{partner.name}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Opponent Team */}
          <div className={`bg-slate-800 rounded-2xl p-6 border-2 ${!declarerWon ? 'border-green-500' : 'border-slate-700'}`}>
            <div className="text-center">
              <div className="text-sm text-slate-400 mb-2">Opponent Team</div>
              <div className="text-4xl font-bold text-red-400 mb-3">{opponentTeamScore}</div>
              <div className="space-y-2">
                {gameState.players
                  .filter((p) => !p.is_declarer && !p.is_partner)
                  .map((player) => (
                    <div key={player.id} className="bg-slate-700/50 rounded-lg px-3 py-2">
                      <span className="text-white font-semibold">{player.name}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Player Stats Table */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="bg-slate-800 rounded-2xl p-6 mb-8"
        >
          <h3 className="text-white font-semibold mb-4 text-center">Player Statistics</h3>
          <div className="space-y-2">
            {playerStats.map((player, index) => (
              <motion.div
                key={player.name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + index * 0.1 }}
                className={`
                  flex items-center justify-between px-4 py-3 rounded-lg
                  ${player.isMe ? 'bg-blue-900/50 border-2 border-blue-500' : 'bg-slate-700/50'}
                `}
              >
                <div className="flex items-center gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-semibold">{player.name}</span>
                      {player.isMe && (
                        <span className="text-xs bg-blue-700 px-2 py-0.5 rounded">You</span>
                      )}
                    </div>
                    <div className="flex gap-2 text-xs mt-1">
                      {player.isDeclarer && (
                        <span className="text-yellow-400">👑 Declarer</span>
                      )}
                      {player.isPartner && (
                        <span className="text-blue-400">🤝 Partner</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-center">
                    <div className="text-xs text-slate-400">Tricks</div>
                    <div className="text-lg font-bold text-white">{player.tricksWon}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-slate-400">Points</div>
                    <div className="text-2xl font-bold text-green-400">{player.cardPoints}</div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Game Statistics */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="bg-slate-800 rounded-2xl p-6 mb-8"
        >
          <h3 className="text-white font-semibold mb-4 text-center">Game Summary</h3>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-slate-400 text-sm mb-1">Total Tricks</div>
              <div className="text-2xl font-bold text-white">{gameState.trick_number || 12}</div>
            </div>
            <div>
              <div className="text-slate-400 text-sm mb-1">Winning Bid</div>
              <div className="text-2xl font-bold text-white capitalize">
                {gameState.bid_history?.find(b => b.bid_type !== 'pass' && b.bid_type !== null)?.bid_type || 'None'}
              </div>
            </div>
            <div>
              <div className="text-slate-400 text-sm mb-1">Announcements</div>
              <div className="text-2xl font-bold text-white">
                {gameState.announcements?.length || 0}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1 }}
          className="grid grid-cols-2 gap-4"
        >
          <button
            onClick={handlePlayAgain}
            className="px-6 py-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-xl transition-colors"
          >
            🔄 Play Again
          </button>
          <button
            onClick={handleReturnToLobby}
            className="px-6 py-4 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-xl transition-colors"
          >
            🏠 Return to Lobby
          </button>
        </motion.div>
      </motion.div>
    </div>
  )
}
