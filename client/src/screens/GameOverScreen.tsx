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
  const gameOverData = useGameStore((state) => state.gameOverData)

  // Use server-provided scoring data
  const declarerTeamScore = gameOverData?.declarer_team_points ?? gameState.players
    .filter((_p, idx) => idx === gameState.declarer_position || (gameState.partner_revealed && idx === gameState.partner_position))
    .reduce((sum, p) => sum + p.total_points, 0)

  const opponentTeamScore = gameOverData?.opponent_team_points ?? gameState.players
    .filter((_p, idx) => idx !== gameState.declarer_position && !(gameState.partner_revealed && idx === gameState.partner_position))
    .reduce((sum, p) => sum + p.total_points, 0)

  const declarerWon = gameOverData?.winner === 'declarer_team' || declarerTeamScore >= 48

  // Am I on the winning team?
  const amIWinner = myPlayer.is_declarer || myPlayer.is_partner ? declarerWon : !declarerWon

  // Get declarer and partner
  const declarer = gameState.players.find((p) => p.is_declarer)
  const partner = gameState.players.find((p) => p.is_partner)

  // Get player stats with final scores
  const playerStats = gameState.players.map((player, idx) => ({
    name: player.name,
    cardPoints: player.total_points,
    tricksWon: player.tricks_won_count || 0,
    finalScore: gameOverData?.player_scores?.[idx] ?? 50,
    scoreChange: gameOverData?.player_scores?.[idx] ? (gameOverData.player_scores[idx] - 50) : 0,
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
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <div className="text-xs text-slate-400">Tricks</div>
                    <div className="text-lg font-bold text-white">{player.tricksWon}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-slate-400">Card Pts</div>
                    <div className="text-lg font-bold text-green-400">{player.cardPoints}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs text-slate-400">Final Score</div>
                    <div className="flex items-center gap-1">
                      <div className={`text-2xl font-bold ${player.scoreChange >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {player.finalScore}
                      </div>
                      <div className={`text-sm ${player.scoreChange >= 0 ? 'text-green-300' : 'text-red-300'}`}>
                        ({player.scoreChange >= 0 ? '+' : ''}{player.scoreChange})
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Game Value */}
        {gameOverData && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="bg-slate-800 rounded-2xl p-6 mb-4"
          >
            <h3 className="text-white font-semibold mb-4 text-center">Game Value</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <div className="text-slate-400 text-sm mb-1">Base Value</div>
                <div className="text-2xl font-bold text-white">{gameOverData.base_game_value}</div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-1">Multiplier</div>
                <div className="text-2xl font-bold text-purple-400">×{gameOverData.game_multiplier}</div>
              </div>
              <div>
                <div className="text-slate-400 text-sm mb-1">Final Value</div>
                <div className="text-3xl font-bold text-yellow-400">{gameOverData.final_game_value}</div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Announcements */}
        {gameOverData && (gameOverData.achieved_announcements?.length > 0 || gameOverData.failed_announcements?.length > 0) && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="bg-slate-800 rounded-2xl p-6 mb-8"
          >
            <h3 className="text-white font-semibold mb-4 text-center">Announcements</h3>
            <div className="space-y-2">
              {gameOverData.achieved_announcements?.map((ann: any, idx: number) => (
                <div key={idx} className="bg-green-900/30 border border-green-500/50 rounded-lg px-4 py-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-green-400">✓</span>
                      <span className="text-white font-semibold capitalize">{ann.announcement_type.replace('_', ' ')}</span>
                      <span className="text-slate-400 text-sm">
                        by {gameState.players[ann.player_position]?.name}
                      </span>
                      {ann.announced && <span className="text-xs bg-yellow-600/50 px-2 py-0.5 rounded">Announced</span>}
                      {!ann.announced && <span className="text-xs bg-slate-600/50 px-2 py-0.5 rounded">Silent</span>}
                    </div>
                    <div className="text-green-400 font-bold">+{ann.points} pts</div>
                  </div>
                </div>
              ))}
              {gameOverData.failed_announcements?.map((ann: any, idx: number) => (
                <div key={idx} className="bg-red-900/30 border border-red-500/50 rounded-lg px-4 py-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-red-400">✗</span>
                      <span className="text-white font-semibold capitalize">{ann.announcement_type.replace('_', ' ')}</span>
                      <span className="text-slate-400 text-sm">
                        by {gameState.players[ann.player_position]?.name}
                      </span>
                      <span className="text-xs bg-red-600/50 px-2 py-0.5 rounded">Failed</span>
                    </div>
                    <div className="text-red-400 font-bold">{ann.points} pts</div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

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
