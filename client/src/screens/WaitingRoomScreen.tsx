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
    <div className="screen-scroll app-backdrop p-4 md:p-6">
      <div className="mx-auto flex min-h-full w-full max-w-7xl flex-col gap-6 lg:flex-row">
        {/* Main Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="min-w-0 flex-1 flex flex-col"
        >
        {/* Header */}
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h2 className="text-3xl font-bold text-white">Waiting Room</h2>
            <p className="text-slate-400 mt-1 break-all">Room: {roomState.room_id}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleLeaveRoom}
              className="btn btn-danger text-sm"
            >
              Leave Room
            </button>
            <button
              onClick={handleReady}
              className={`btn px-6 py-2 text-sm ${
                isReady
                  ? 'btn-success'
                  : 'btn-primary'
              }`}
            >
              {isReady ? 'Ready' : 'Mark Ready'}
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
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          {[0, 1, 2, 3].map((position) => {
            const player = roomState.players.find((p) => p.position === position)

            return (
              <motion.div
                key={position}
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: position * 0.1 }}
                className={`
                  room-card rounded-xl p-6 text-center
                  ${player ? 'border-slate-500/60' : 'border-dashed border-slate-700'}
                `}
              >
                <div className={`
                  mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full border font-black
                  ${player ? 'bg-slate-700 border-slate-500 text-white' : 'bg-slate-900/60 border-dashed border-slate-600 text-slate-500'}
                `}>
                  {player ? player.name.slice(0, 1).toUpperCase() : '+'}
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
                        Ready
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
        <div className="glass-panel rounded-xl p-6">
          <p className="text-slate-300 text-sm mb-2">
            Share room code with friends:
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <div className="flex-1 px-4 py-3 bg-slate-950/45 border border-slate-600/50 rounded-lg text-center overflow-hidden">
              <span className="text-lg md:text-2xl font-mono font-bold text-white tracking-wider break-all">
                {roomState.room_id}
              </span>
            </div>
            <button
              onClick={handleCopyRoomCode}
              className="btn btn-primary px-6 py-3"
            >
              Copy
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
            All players ready. Game starting...
          </motion.div>
        )}
        </motion.div>

        {/* Chat Sidebar */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-full lg:w-96 h-[360px] lg:sticky lg:top-6 lg:h-[calc(100vh-3rem)]"
        >
          <Chat className="h-full" />
        </motion.div>
      </div>
    </div>
  )
}
