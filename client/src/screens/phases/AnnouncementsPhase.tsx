import { motion } from 'framer-motion'
import { useState } from 'react'
import { socketManager } from '@/services/socketManager'
import Hand from '@/components/Hand'
import PlayerAvatar from '@/components/PlayerAvatar'
import type { GameState, Announcement } from '@/types'

interface AnnouncementsPhaseProps {
  gameState: GameState
  playerPosition: number
}

const announcementTypes = [
  {
    value: 'trull',
    label: 'Trull',
    description: 'I, XXI, Škis',
    icon: '🎯',
    points: { announced: 2, silent: 1 },
  },
  {
    value: 'four_kings',
    label: 'Four Kings',
    description: 'All 4 Kings',
    icon: '👑',
    points: { announced: 2, silent: 1 },
  },
  {
    value: 'double_game',
    label: 'Double Game',
    description: '2x points',
    icon: '2️⃣',
    points: { announced: 0, silent: 0 },
  },
  {
    value: 'volat',
    label: 'Volat',
    description: 'Win all tricks',
    icon: '💯',
    points: { announced: 8, silent: 4 },
  },
  {
    value: 'pagat_ultimo',
    label: 'Pagát Ultimó',
    description: 'Win last trick with I',
    icon: '🎴',
    points: { announced: 8, silent: 4 },
  },
  {
    value: 'xxi_catch',
    label: 'XXI Catch',
    description: 'Capture XXI',
    icon: '🎣',
    points: { announced: 8, silent: 4 },
  },
]

export default function AnnouncementsPhase({
  gameState,
  playerPosition,
}: AnnouncementsPhaseProps) {
  const [selectedAnnouncements, setSelectedAnnouncements] = useState<string[]>([])

  const isMyTurn = gameState.current_turn === playerPosition
  const currentPlayer = gameState.players[gameState.current_turn]
  const myPlayer = gameState.players[playerPosition]

  // Get valid announcements (would come from server in real implementation)
  // If server doesn't provide valid_announcements, allow all announcements for now
  const validAnnouncements = gameState.valid_announcements && gameState.valid_announcements.length > 0
    ? gameState.valid_announcements
    : announcementTypes.map(a => a.value)

  const toggleAnnouncement = (announcementType: string) => {
    setSelectedAnnouncements((prev) => {
      if (prev.includes(announcementType)) {
        // Remove if already selected
        return prev.filter((type) => type !== announcementType)
      }
      // Add new announcement
      return [...prev, announcementType]
    })
  }

  const handleConfirmAnnouncements = () => {
    if (selectedAnnouncements.length > 0) {
      // Send all announcements to server (always announced: true)
      selectedAnnouncements.forEach((announcementType) => {
        socketManager.makeAnnouncement(announcementType, true)
      })
      setSelectedAnnouncements([])
    }
  }

  const handlePass = () => {
    socketManager.passAnnouncement()
  }

  // Count consecutive passes
  const consecutivePasses = gameState.announcement_history
    ? gameState.announcement_history
        .slice()
        .reverse()
        .findIndex((a) => a !== null)
    : 0

  return (
    <div className="w-full max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-4 shadow-2xl"
      >
        {/* Header */}
        <div className="text-center mb-3">
          <h2 className="text-xl font-bold text-white mb-1">Announcements</h2>
          <p className="text-slate-300 text-sm">
            {isMyTurn ? (
              <span className="text-yellow-400 font-semibold">Your turn to announce</span>
            ) : (
              <>
                Waiting for{' '}
                <span className="text-yellow-400 font-semibold">{currentPlayer.name}</span>
              </>
            )}
          </p>
          {consecutivePasses > 0 && (
            <p className="text-slate-400 text-xs mt-1">
              {consecutivePasses} consecutive pass{consecutivePasses !== 1 ? 'es' : ''} (need 3 to end)
            </p>
          )}
        </div>

        {/* Announcement History */}
        {gameState.announcements && gameState.announcements.length > 0 && (
          <div className="mb-3 bg-slate-700/50 rounded-xl p-2">
            <h3 className="text-white font-semibold mb-2 text-xs">Announcements Made</h3>
            <div className="space-y-2">
              {gameState.announcements.map((announcement: Announcement, index: number) => {
                const announcementInfo = announcementTypes.find(
                  (a) => a.value === announcement.announcement_type
                )
                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="flex items-center justify-between text-sm bg-slate-600/50 rounded-lg p-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-2xl">{announcementInfo?.icon}</span>
                      <div>
                        <div className="text-white font-semibold">
                          {announcementInfo?.label}
                        </div>
                        <div className="text-slate-400 text-xs">
                          {gameState.players[announcement.player_position]?.name}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div
                        className={`font-semibold ${
                          announcement.announced ? 'text-yellow-400' : 'text-slate-400'
                        }`}
                      >
                        {announcement.announced ? 'Announced' : 'Silent'}
                      </div>
                      {announcementInfo && (
                        <div className="text-slate-400 text-xs">
                          +
                          {announcement.announced
                            ? announcementInfo.points.announced
                            : announcementInfo.points.silent}{' '}
                          pts
                        </div>
                      )}
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </div>
        )}

        {isMyTurn ? (
          <div className="space-y-3">
            {/* Info */}
            <div className="bg-blue-900/30 border border-blue-700/50 rounded-lg p-2 text-xs text-blue-200">
              💡 Click to announce. You can select multiple announcements.
            </div>

            {/* Announcement Selection Grid */}
            <div className="grid grid-cols-3 gap-3">
              {announcementTypes.map((announcement) => {
                const isValid = validAnnouncements.includes(announcement.value)
                const isSelected = selectedAnnouncements.includes(announcement.value)

                return (
                  <motion.button
                    key={announcement.value}
                    disabled={!isValid}
                    whileHover={isValid ? { scale: 1.05 } : undefined}
                    whileTap={isValid ? { scale: 0.95 } : undefined}
                    onClick={() => {
                      if (isValid) {
                        toggleAnnouncement(announcement.value)
                      }
                    }}
                    className={`
                      px-3 py-4 rounded-xl font-semibold text-left
                      transition-all duration-200
                      ${
                        isSelected
                          ? 'bg-blue-600 text-white ring-4 ring-blue-400 scale-105'
                          : isValid
                          ? 'bg-slate-700 text-white hover:bg-slate-600'
                          : 'bg-slate-800 text-slate-600 cursor-not-allowed opacity-50'
                      }
                    `}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{announcement.icon}</span>
                      <span className="text-sm font-bold">{announcement.label}</span>
                    </div>
                    <div className="text-xs opacity-80 mb-1">{announcement.description}</div>
                    <div className="text-xs opacity-70">
                      📢 +{announcement.points.announced} | 🤫 +{announcement.points.silent}
                    </div>
                    {isSelected && (
                      <div className="mt-2 text-center text-lg">
                        📢
                      </div>
                    )}
                  </motion.button>
                )
              })}
            </div>

            {/* Selected Announcements Summary */}
            {selectedAnnouncements.length > 0 && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-green-900/30 border border-green-700/50 rounded-lg p-2"
              >
                <h4 className="text-green-200 font-semibold mb-1.5 text-xs">
                  Selected ({selectedAnnouncements.length}):
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {selectedAnnouncements.map((announcementType) => {
                    const info = announcementTypes.find((a) => a.value === announcementType)
                    return (
                      <div
                        key={announcementType}
                        className="bg-slate-700 text-white px-2 py-0.5 rounded text-[10px] flex items-center gap-1"
                      >
                        <span>{info?.icon}</span>
                        <span>{info?.label}</span>
                        <span>📢</span>
                      </div>
                    )
                  })}
                </div>
              </motion.div>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-2">
              <motion.button
                whileHover={selectedAnnouncements.length > 0 ? { scale: 1.02 } : undefined}
                whileTap={selectedAnnouncements.length > 0 ? { scale: 0.98 } : undefined}
                onClick={handleConfirmAnnouncements}
                disabled={selectedAnnouncements.length === 0}
                className={`
                  px-3 py-2 rounded-xl font-semibold text-white text-sm
                  transition-all duration-200
                  ${
                    selectedAnnouncements.length > 0
                      ? 'bg-green-600 hover:bg-green-700 shadow-lg'
                      : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  }
                `}
              >
                {selectedAnnouncements.length > 0
                  ? `✓ Confirm (${selectedAnnouncements.length})`
                  : '✓ Confirm'}
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handlePass}
                className="px-3 py-2 bg-slate-600 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors text-sm"
              >
                Pass
              </motion.button>
            </div>
          </div>
        ) : (
          /* Waiting Message */
          <div className="text-center py-4">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-4xl mb-2"
            >
              ⏳
            </motion.div>
            <p className="text-slate-400 text-sm">Waiting for {currentPlayer.name}...</p>
          </div>
        )}
      </motion.div>

      {/* Player's Hand - Always visible during announcements */}
      {myPlayer.hand && myPlayer.hand.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mt-4 bg-slate-800/90 backdrop-blur-sm rounded-2xl px-4 py-2 shadow-2xl relative"
        >
          {/* Player Avatar in upper left corner */}
          <div className="absolute top-2 left-2 z-10">
            <PlayerAvatar
              player={myPlayer}
              isCurrentTurn={gameState.current_turn === playerPosition}
              position={playerPosition as 0 | 1 | 2 | 3}
              isLocalPlayer={true}
            />
          </div>

          <Hand
            cards={myPlayer.hand}
            layout="fan"
            size="md"
          />
        </motion.div>
      )}
    </div>
  )
}
