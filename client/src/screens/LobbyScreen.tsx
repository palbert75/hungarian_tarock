import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'

export default function LobbyScreen() {
  const playerName = useGameStore((state) => state.playerName)
  const availableRooms = useGameStore((state) => state.availableRooms)
  const addToast = useGameStore((state) => state.addToast)
  const [roomCode, setRoomCode] = useState('')
  const [showBrowser, setShowBrowser] = useState(false)

  const handleCreateRoom = () => {
    console.log('[Lobby] Creating new room...')
    socketManager.joinRoom() // No room ID = create new
  }

  const handleJoinRoom = () => {
    if (!roomCode.trim()) {
      addToast({
        type: 'error',
        message: 'Please enter a room code',
      })
      return
    }

    console.log('[Lobby] Joining room:', roomCode.trim())
    socketManager.joinRoom(roomCode.trim())
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleJoinRoom()
    }
  }

  const handleLogout = () => {
    // Disconnect from socket
    socketManager.disconnect()

    // Clear all persisted session data
    useGameStore.persist.clearStorage()

    // Reload the page to reset everything
    window.location.reload()
  }

  const handleBrowseRooms = () => {
    setShowBrowser(true)
    socketManager.listRooms()
  }

  const handleJoinFromBrowser = (roomId: string) => {
    console.log('[Lobby] Joining room from browser:', roomId)
    socketManager.joinRoom(roomId)
  }

  const handleRefreshRooms = () => {
    socketManager.listRooms()
    addToast({
      type: 'info',
      message: 'Refreshing room list...',
    })
  }

  // Auto-refresh rooms every 5 seconds when browser is open
  useEffect(() => {
    if (showBrowser) {
      const interval = setInterval(() => {
        socketManager.listRooms()
      }, 5000)
      return () => clearInterval(interval)
    }
  }, [showBrowser])

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
              onClick={handleBrowseRooms}
              className="flex-1 py-4 px-6 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-white font-semibold rounded-lg transition-all transform hover:scale-105 active:scale-95 shadow-lg"
            >
              <div className="text-2xl mb-2">🔍</div>
              <div>Browse Rooms</div>
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
                value={roomCode}
                onChange={(e) => setRoomCode(e.target.value)}
                onKeyPress={handleKeyPress}
                className="flex-1 px-4 py-2 bg-slate-700 text-white rounded-lg border-2 border-slate-600 focus:border-blue-500 focus:outline-none transition-colors uppercase"
                maxLength={36}
              />
              <button
                onClick={handleJoinRoom}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
              >
                Join
              </button>
            </div>
          </div>
        </div>

      </motion.div>

      {/* Room Browser Modal */}
      <AnimatePresence>
        {showBrowser && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
            onClick={() => setShowBrowser(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-slate-800 rounded-2xl p-6 max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col shadow-2xl"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-white">🔍 Browse Rooms</h2>
                  <p className="text-slate-400 text-sm mt-1">
                    {availableRooms.length} room{availableRooms.length !== 1 ? 's' : ''} available
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleRefreshRooms}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                  >
                    🔄 Refresh
                  </button>
                  <button
                    onClick={() => setShowBrowser(false)}
                    className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
                  >
                    ✕ Close
                  </button>
                </div>
              </div>

              {/* Room List */}
              <div className="flex-1 overflow-y-auto space-y-3">
                {availableRooms.length === 0 ? (
                  <div className="text-center py-12">
                    <div className="text-6xl mb-4">🎴</div>
                    <p className="text-slate-400 text-lg">No rooms available</p>
                    <p className="text-slate-500 text-sm mt-2">Create one to get started!</p>
                  </div>
                ) : (
                  availableRooms.map((room) => (
                    <motion.div
                      key={room.room_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-slate-700/50 rounded-xl p-4 hover:bg-slate-700 transition-colors"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-white font-semibold">
                              Room #{room.room_id.substring(0, 8)}
                            </h3>
                            <span className="text-sm text-slate-400">
                              {room.players.length}/4 players
                            </span>
                          </div>

                          {/* Player List */}
                          <div className="flex gap-2 flex-wrap">
                            {room.players.map((player) => (
                              <div
                                key={player.id}
                                className="flex items-center gap-1 px-3 py-1 bg-slate-600 rounded-lg text-sm"
                              >
                                <span className="text-white">{player.name}</span>
                                {player.is_ready && (
                                  <span className="text-green-400">✓</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>

                        <button
                          onClick={() => handleJoinFromBrowser(room.room_id)}
                          className="ml-4 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                        >
                          Join
                        </button>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
