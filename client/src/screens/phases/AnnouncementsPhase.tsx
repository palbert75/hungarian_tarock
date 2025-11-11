import { motion } from 'framer-motion'
import { useState } from 'react'
import { socketManager } from '@/services/socketManager'
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
  const [selectedAnnouncement, setSelectedAnnouncement] = useState<string | null>(null)
  const [announcedChoice, setAnnouncedChoice] = useState<boolean>(true)

  const isMyTurn = gameState.current_turn === playerPosition
  const currentPlayer = gameState.players[gameState.current_turn]

  // Get valid announcements (would come from server in real implementation)
  const validAnnouncements = gameState.valid_announcements || []

  const handleAnnounce = () => {
    if (selectedAnnouncement) {
      socketManager.makeAnnouncement(selectedAnnouncement, announcedChoice)
      setSelectedAnnouncement(null)
      setAnnouncedChoice(true)
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
        className="bg-slate-800/90 backdrop-blur-sm rounded-2xl p-8 shadow-2xl"
      >
        {/* Header */}
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold text-white mb-2">Announcements</h2>
          <p className="text-slate-300">
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
            <p className="text-slate-400 text-sm mt-1">
              {consecutivePasses} consecutive pass{consecutivePasses !== 1 ? 'es' : ''} (need 3 to end)
            </p>
          )}
        </div>

        {/* Announcement History */}
        {gameState.announcements && gameState.announcements.length > 0 && (
          <div className="mb-6 bg-slate-700/50 rounded-xl p-4">
            <h3 className="text-white font-semibold mb-3 text-sm">Announcements Made</h3>
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
          <div className="space-y-4">
            {/* Announcement Selection */}
            <div className="grid grid-cols-2 gap-3">
              {announcementTypes.map((announcement) => {
                const isValid = validAnnouncements.includes(announcement.value)
                const isSelected = selectedAnnouncement === announcement.value

                return (
                  <motion.button
                    key={announcement.value}
                    whileHover={isValid ? { scale: 1.02 } : undefined}
                    whileTap={isValid ? { scale: 0.98 } : undefined}
                    onClick={() => isValid && setSelectedAnnouncement(announcement.value)}
                    disabled={!isValid}
                    className={`
                      px-4 py-3 rounded-xl font-semibold text-left
                      transition-all duration-200
                      ${
                        isSelected
                          ? 'bg-blue-600 text-white ring-4 ring-blue-400'
                          : isValid
                          ? 'bg-slate-700 text-white hover:bg-slate-600'
                          : 'bg-slate-800 text-slate-600 cursor-not-allowed'
                      }
                    `}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-2xl">{announcement.icon}</span>
                      <span className="text-base">{announcement.label}</span>
                    </div>
                    <div className="text-xs opacity-80 ml-9">{announcement.description}</div>
                    <div className="text-xs opacity-70 ml-9 mt-1">
                      Announced: +{announcement.points.announced} | Silent: +
                      {announcement.points.silent}
                    </div>
                  </motion.button>
                )
              })}
            </div>

            {/* Announced/Silent Choice */}
            {selectedAnnouncement && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-slate-700/50 rounded-xl p-4"
              >
                <h4 className="text-white font-semibold mb-3 text-sm">How to announce?</h4>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => setAnnouncedChoice(true)}
                    className={`
                      px-4 py-3 rounded-lg font-semibold transition-all
                      ${
                        announcedChoice
                          ? 'bg-yellow-600 text-white'
                          : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
                      }
                    `}
                  >
                    📢 Announced
                    <div className="text-xs opacity-80 mt-1">More points if successful</div>
                  </button>
                  <button
                    onClick={() => setAnnouncedChoice(false)}
                    className={`
                      px-4 py-3 rounded-lg font-semibold transition-all
                      ${
                        !announcedChoice
                          ? 'bg-slate-500 text-white'
                          : 'bg-slate-600 text-slate-300 hover:bg-slate-500'
                      }
                    `}
                  >
                    🤫 Silent
                    <div className="text-xs opacity-80 mt-1">Fewer points, less risk</div>
                  </button>
                </div>
              </motion.div>
            )}

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-3">
              <motion.button
                whileHover={selectedAnnouncement ? { scale: 1.02 } : undefined}
                whileTap={selectedAnnouncement ? { scale: 0.98 } : undefined}
                onClick={handleAnnounce}
                disabled={!selectedAnnouncement}
                className={`
                  px-6 py-4 rounded-xl font-semibold text-white text-lg
                  transition-all duration-200
                  ${
                    selectedAnnouncement
                      ? 'bg-green-600 hover:bg-green-700 shadow-lg'
                      : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  }
                `}
              >
                ✓ Confirm
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={handlePass}
                className="px-6 py-4 bg-slate-600 hover:bg-slate-700 text-white font-semibold rounded-xl transition-colors text-lg"
              >
                Pass
              </motion.button>
            </div>
          </div>
        ) : (
          /* Waiting Message */
          <div className="text-center py-8">
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="text-6xl mb-4"
            >
              ⏳
            </motion.div>
            <p className="text-slate-400">Waiting for {currentPlayer.name}...</p>
          </div>
        )}
      </motion.div>
    </div>
  )
}
