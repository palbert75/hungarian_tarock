import { motion } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'

export default function GameScreen() {
  const gameState = useGameStore((state) => state.gameState)
  const playerPosition = useGameStore((state) => state.playerPosition)

  if (!gameState || playerPosition === null) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-table-green">
        <div className="text-white text-xl">Loading game...</div>
      </div>
    )
  }

  const myPlayer = gameState.players[playerPosition]

  return (
    <div className="w-full h-full bg-table-green relative overflow-hidden">
      {/* Top Bar */}
      <div className="absolute top-0 left-0 right-0 bg-slate-900/90 backdrop-blur-sm px-6 py-4 flex items-center justify-between z-10">
        <div className="flex items-center gap-6">
          <div className="text-white font-semibold">
            🎴 Room: {gameState.game_id.substring(0, 8)}
          </div>
          <div className="text-slate-300 text-sm">
            Phase: <span className="text-blue-400 font-semibold capitalize">{gameState.phase}</span>
          </div>
          <div className="text-slate-300 text-sm">
            Turn: <span className="text-yellow-400 font-semibold">
              {gameState.players[gameState.current_turn]?.name}
            </span>
          </div>
        </div>
        <button className="text-white/80 hover:text-white transition-colors">
          ⚙️ Menu
        </button>
      </div>

      {/* Main Game Area */}
      <div className="w-full h-full flex items-center justify-center pt-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-12 max-w-2xl shadow-2xl"
        >
          <div className="text-center">
            <h2 className="text-4xl font-bold text-white mb-4">
              🎴 Game Started!
            </h2>
            <p className="text-slate-300 text-lg mb-8">
              Current Phase: <span className="text-blue-400 font-semibold capitalize">{gameState.phase}</span>
            </p>

            {/* Player Info */}
            <div className="bg-slate-700/50 rounded-xl p-6 mb-6">
              <h3 className="text-white font-semibold mb-4">Your Info:</h3>
              <div className="text-slate-300 space-y-2">
                <p>Name: <span className="text-white font-semibold">{myPlayer.name}</span></p>
                <p>Position: <span className="text-white font-semibold">{playerPosition}</span></p>
                <p>Hand Size: <span className="text-white font-semibold">{myPlayer.hand_size} cards</span></p>
                {myPlayer.is_declarer && (
                  <p className="text-gold font-semibold">👑 You are the Declarer!</p>
                )}
              </div>
            </div>

            {/* All Players */}
            <div className="bg-slate-700/50 rounded-xl p-6">
              <h3 className="text-white font-semibold mb-4">Players:</h3>
              <div className="grid grid-cols-2 gap-3">
                {gameState.players.map((player, idx) => (
                  <div
                    key={player.id}
                    className={`
                      px-4 py-2 rounded-lg text-sm
                      ${idx === playerPosition ? 'bg-blue-600 text-white' : 'bg-slate-600 text-slate-200'}
                      ${idx === gameState.current_turn ? 'ring-2 ring-yellow-400' : ''}
                    `}
                  >
                    <div className="font-semibold">{player.name}</div>
                    <div className="text-xs opacity-80">{player.hand_size} cards</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Coming Soon Note */}
            <div className="mt-8 text-slate-400 text-sm">
              <p>🚧 Full game interface coming soon!</p>
              <p className="mt-2">Use the test client to play for now.</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
