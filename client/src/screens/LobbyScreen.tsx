import { motion } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'

export default function LobbyScreen() {
  const playerName = useGameStore((state) => state.playerName)

  const handleCreateRoom = () => {
    socketManager.joinRoom() // No room ID = create new
  }

  const handleLogout = () => {
    socketManager.disconnect()
    window.location.reload()
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-2xl px-6"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-white">🏠 Lobby</h2>
            <p className="text-slate-400 mt-1">Welcome, {playerName}!</p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            Logout
          </button>
        </div>

        {/* Actions */}
        <div className="bg-slate-800 rounded-xl p-8 shadow-2xl">
          <div className="flex gap-4 mb-8">
            <button
              onClick={handleCreateRoom}
              className="flex-1 py-4 px-6 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-lg transition-all transform hover:scale-105 active:scale-95 shadow-lg"
            >
              <div className="text-2xl mb-2">🎮</div>
              <div>Create Room</div>
            </button>
            <button
              className="flex-1 py-4 px-6 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition-all transform hover:scale-105 active:scale-95 opacity-50 cursor-not-allowed"
              disabled
            >
              <div className="text-2xl mb-2">🔍</div>
              <div>Browse Rooms</div>
              <div className="text-xs mt-1">(Coming soon)</div>
            </button>
          </div>

          {/* Quick Join */}
          <div className="border-t border-slate-700 pt-6">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Or enter room code:
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Room code..."
                className="flex-1 px-4 py-2 bg-slate-700 text-white rounded-lg border-2 border-slate-600 focus:border-blue-500 focus:outline-none transition-colors"
                maxLength={6}
              />
              <button className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors">
                Join
              </button>
            </div>
          </div>
        </div>

        {/* Coming Soon Features */}
        <div className="mt-6 text-center text-slate-500 text-sm">
          <p>📊 Room browser and statistics coming soon!</p>
        </div>
      </motion.div>
    </div>
  )
}
