import { motion } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import Chat from '@/components/Chat'

export default function WaitingRoomScreen() {
  const roomState = useGameStore((state) => state.roomState)
  const playerName = useGameStore((state) => state.playerName)

  if (!roomState) return null

  const myPlayer = roomState.players.find((p) => p.name === playerName)
  const isReady = myPlayer?.is_ready || false

  const handleReady = () => {
    socketManager.ready()
  }

  const handleLeaveRoom = () => {
    // Save player name before clearing
    const playerName = useGameStore.getState().playerName

    // Leave the room via socket
    socketManager.leaveRoom()

    // Clear persisted session data
    useGameStore.persist.clearStorage()

    // Restore player name so user doesn't have to re-enter it
    if (playerName) {
      useGameStore.getState().setPlayerInfo('', playerName)
    }

    console.log('[WaitingRoomScreen] Left room and cleared session storage')
  }

  const handleCopyRoomCode = () => {
    navigator.clipboard.writeText(roomState.room_id)
    useGameStore.getState().addToast({
      type: 'success',
      message: 'Room code copied!',
    })
  }

  return (
    <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
      <div className="w-full max-w-7xl h-full flex flex-col lg:flex-row gap-6">
        {/* Main Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 flex flex-col"
        >
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-white">Waiting Room</h2>
            <p className="text-slate-400 mt-1">Room: {roomState.room_id}</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleLeaveRoom}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
            >
              Leave Room
            </button>
            <button
              onClick={handleReady}
              className={`px-6 py-2 font-semibold rounded-lg transition-colors ${
                isReady
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
            >
              {isReady ? '✅ Ready' : 'Mark Ready'}
            </button>
          </div>
        </div>

        {/* Waiting message */}
        {!roomState.is_full && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center mb-8"
          >
            <p className="text-2xl text-slate-300 font-medium">
              Waiting for players...
            </p>
            <p className="text-slate-400 mt-2">
              {roomState.players.length}/4 players joined
            </p>
          </motion.div>
        )}

        {/* Player Grid */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          {[0, 1, 2, 3].map((position) => {
            const player = roomState.players.find((p) => p.position === position)

            return (
              <motion.div
                key={position}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: position * 0.1 }}
                className={`
                  bg-slate-800 rounded-xl p-6 text-center
                  ${player ? 'border-2 border-slate-600' : 'border-2 border-dashed border-slate-700'}
                `}
              >
                <div className="text-4xl mb-3">
                  {player ? (
                    player.name === playerName ? '👤' : '🎮'
                  ) : '⏳'}
                </div>

                <h3 className="text-lg font-semibold text-white mb-2">
                  Position {position}
                </h3>

                {player ? (
                  <>
                    <p className="text-slate-300 font-medium mb-2">
                      {player.name}
                      {player.name === playerName && (
                        <span className="text-blue-400"> (You)</span>
                      )}
                    </p>
                    <div className="flex items-center justify-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          player.is_connected ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      />
                      <span className="text-sm text-slate-400">
                        {player.is_connected ? 'Online' : 'Offline'}
                      </span>
                    </div>
                    {player.is_ready && (
                      <div className="mt-2 text-green-400 font-semibold">
                        ✅ Ready
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-slate-500 italic">Empty</p>
                )}
              </motion.div>
            )
          })}
        </div>

        {/* Share Room Code */}
        <div className="bg-slate-800 rounded-xl p-6">
          <p className="text-slate-300 text-sm mb-2">
            Share room code with friends:
          </p>
          <div className="flex gap-2">
            <div className="flex-1 px-4 py-3 bg-slate-700 rounded-lg text-center">
              <span className="text-2xl font-mono font-bold text-white tracking-wider">
                {roomState.room_id}
              </span>
            </div>
            <button
              onClick={handleCopyRoomCode}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
            >
              📋 Copy
            </button>
          </div>
        </div>

        {/* Game starts hint */}
        {roomState.players.every((p) => p.is_ready) && roomState.is_full && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 text-center text-green-400 font-semibold"
          >
            🎉 All players ready! Game starting...
          </motion.div>
        )}
        </motion.div>

        {/* Chat Sidebar */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-full lg:w-96 h-[400px] lg:h-full"
        >
          <Chat className="h-full" />
        </motion.div>
      </div>
    </div>
  )
}
