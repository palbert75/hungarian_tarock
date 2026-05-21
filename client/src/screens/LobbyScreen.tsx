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
    <div className="screen-scroll app-backdrop p-4 md:p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto flex min-h-full w-full max-w-2xl flex-col justify-center py-8"
      >
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-3xl font-bold text-white">Lobby</h2>
            <p className="text-slate-400 mt-1">Welcome, {playerName}!</p>
          </div>
          <button
            onClick={handleLogout}
            className="btn btn-muted text-sm"
          >
            Logout
          </button>
        </div>

        {/* Actions */}
        <div className="glass-panel rounded-xl p-6 md:p-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <button
              onClick={handleCreateRoom}
              className="room-card py-5 px-6 text-white font-semibold rounded-xl transition-all hover:-translate-y-1 hover:border-blue-400/60"
            >
              <div className="mb-3 text-sm uppercase tracking-wide text-blue-300">New Table</div>
              <div className="text-xl">Create Room</div>
            </button>
            <button
              onClick={handleBrowseRooms}
              className="room-card py-5 px-6 text-white font-semibold rounded-xl transition-all hover:-translate-y-1 hover:border-purple-400/60"
            >
              <div className="mb-3 text-sm uppercase tracking-wide text-purple-300">Open Tables</div>
              <div className="text-xl">Browse Rooms</div>
            </button>
          </div>

          {/* Quick Join */}
          <div className="border-t border-slate-700 pt-6">
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Or enter room code:
            </label>
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                placeholder="Room code..."
                value={roomCode}
                onChange={(e) => setRoomCode(e.target.value)}
                onKeyPress={handleKeyPress}
                className="input-field flex-1 uppercase"
                maxLength={36}
              />
              <button
                onClick={handleJoinRoom}
                className="btn btn-primary px-6"
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
            className="fixed inset-0 bg-black/70 flex items-start justify-center z-50 overflow-y-auto p-4 md:items-center"
            onClick={() => setShowBrowser(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-panel rounded-xl p-4 md:p-6 max-w-3xl w-full max-h-[calc(100vh-2rem)] overflow-hidden flex flex-col"
            >
              {/* Header */}
              <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h2 className="text-2xl font-bold text-white">Browse Rooms</h2>
                  <p className="text-slate-400 text-sm mt-1">
                    {availableRooms.length} room{availableRooms.length !== 1 ? 's' : ''} available
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleRefreshRooms}
                    className="btn btn-primary text-sm"
                  >
                    Refresh
                  </button>
                  <button
                    onClick={() => setShowBrowser(false)}
                    className="btn btn-muted text-sm"
                  >
                    Close
                  </button>
                </div>
              </div>

              {/* Room List */}
              <div className="flex-1 overflow-y-auto space-y-3">
                {availableRooms.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-slate-400 text-lg">No rooms available</p>
                    <p className="text-slate-500 text-sm mt-2">Create one to get started!</p>
                  </div>
                ) : (
                  availableRooms.map((room) => (
                    <motion.div
                      key={room.room_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="room-card rounded-xl p-4 hover:border-blue-400/50 transition-colors"
                    >
                      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0 flex-1">
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
                                className="flex items-center gap-1 px-3 py-1 bg-slate-800/80 border border-slate-600/40 rounded-lg text-sm"
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
                          className="btn btn-primary px-6 py-2 sm:ml-4"
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
