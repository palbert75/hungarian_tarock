import { useState } from 'react'
import { motion } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'

export default function ConnectionScreen() {
  const [name, setName] = useState('')
  const [isConnecting, setIsConnecting] = useState(false)
  const connectionStatus = useGameStore((state) => state.connectionStatus)
  const addToast = useGameStore((state) => state.addToast)

  const handleConnect = async () => {
    if (!name.trim()) {
      addToast({
        type: 'error',
        message: 'Please enter your name',
      })
      return
    }

    if (name.trim().length < 2) {
      addToast({
        type: 'error',
        message: 'Name must be at least 2 characters',
      })
      return
    }

    setIsConnecting(true)

    try {
      await socketManager.connect(name.trim())
      // Store will be updated by socket manager
    } catch (error) {
      setIsConnecting(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleConnect()
    }
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md px-6"
      >
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="text-center mb-12"
        >
          <h1 className="font-display text-6xl font-bold text-gradient mb-4">
            🎴 Hungarian Tarokk
          </h1>
          <p className="text-slate-400 text-lg">
            Online Multiplayer Card Game
          </p>
        </motion.div>

        {/* Connection Form */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="bg-slate-800 rounded-xl p-8 shadow-2xl"
        >
          <div className="mb-6">
            <label
              htmlFor="player-name"
              className="block text-sm font-medium text-slate-300 mb-2"
            >
              Enter Your Name
            </label>
            <input
              id="player-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Your name..."
              disabled={isConnecting}
              maxLength={20}
              className="
                w-full px-4 py-3 rounded-lg
                bg-slate-700 text-white
                border-2 border-slate-600
                focus:border-blue-500 focus:outline-none
                transition-colors
                disabled:opacity-50 disabled:cursor-not-allowed
              "
              autoFocus
            />
          </div>

          <button
            onClick={handleConnect}
            disabled={isConnecting || !name.trim() || name.trim().length < 2}
            className="
              w-full py-3 px-6 rounded-lg
              bg-gradient-to-r from-blue-600 to-blue-700
              hover:from-blue-700 hover:to-blue-800
              text-white font-semibold
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200
              transform hover:scale-105 active:scale-95
              shadow-lg hover:shadow-xl
            "
          >
            {isConnecting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin">⏳</span>
                Connecting...
              </span>
            ) : connectionStatus === 'error' ? (
              'Retry Connection'
            ) : (
              'Connect to Game'
            )}
          </button>

          {connectionStatus === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 text-center text-red-400 text-sm"
            >
              Failed to connect. Please check server status.
            </motion.div>
          )}
        </motion.div>

        {/* Footer Links */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-center flex items-center justify-center gap-6"
        >
          <button className="text-slate-400 hover:text-white transition-colors text-sm">
            ⚙️ Settings
          </button>
          <button className="text-slate-400 hover:text-white transition-colors text-sm">
            📖 Rules
          </button>
          <button className="text-slate-400 hover:text-white transition-colors text-sm">
            ℹ️ About
          </button>
        </motion.div>

        {/* Version */}
        <div className="mt-8 text-center text-slate-500 text-xs">
          v0.1.0 • Open Source
        </div>
      </motion.div>
    </div>
  )
}
