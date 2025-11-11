import { motion } from 'framer-motion'
import type { Player } from '@/types'

interface PlayerAvatarProps {
  player: Player | null
  isCurrentTurn: boolean
  position: 0 | 1 | 2 | 3
  isLocalPlayer?: boolean
}

const positionLabels = {
  0: 'South',
  1: 'West',
  2: 'North',
  3: 'East',
}

export default function PlayerAvatar({
  player,
  isCurrentTurn,
  position,
  isLocalPlayer = false,
}: PlayerAvatarProps) {
  if (!player) {
    // Empty slot
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="w-20 h-20 rounded-full bg-slate-700/50 border-2 border-dashed border-slate-600 flex items-center justify-center">
          <span className="text-2xl opacity-30">👤</span>
        </div>
        <div className="text-slate-500 text-sm font-medium">
          {positionLabels[position]}
        </div>
      </div>
    )
  }

  return (
    <motion.div
      className="flex flex-col items-center gap-2"
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Avatar with turn indicator */}
      <div className="relative">
        {/* Turn indicator ring */}
        {isCurrentTurn && (
          <motion.div
            className="absolute inset-0 rounded-full border-4 border-yellow-400"
            animate={{
              scale: [1, 1.1, 1],
              opacity: [1, 0.7, 1],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}

        {/* Avatar circle */}
        <div
          className={`
            w-20 h-20 rounded-full flex items-center justify-center text-3xl
            border-4 transition-all duration-300
            ${
              isLocalPlayer
                ? 'bg-blue-600 border-blue-400'
                : 'bg-slate-700 border-slate-600'
            }
            ${isCurrentTurn ? 'ring-4 ring-yellow-400/50' : ''}
          `}
        >
          {isLocalPlayer ? '👤' : '🎮'}
        </div>

        {/* Connection status indicator */}
        <div className="absolute -bottom-1 -right-1">
          <div
            className={`
              w-5 h-5 rounded-full border-2 border-slate-900
              ${player.is_connected ? 'bg-green-500' : 'bg-red-500'}
            `}
            title={player.is_connected ? 'Online' : 'Offline'}
          />
        </div>

        {/* Card count badge */}
        {player.hand_size > 0 && (
          <motion.div
            className="absolute -top-2 -right-2 bg-slate-900 border-2 border-slate-600 rounded-full w-8 h-8 flex items-center justify-center"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
          >
            <span className="text-white text-xs font-bold">{player.hand_size}</span>
          </motion.div>
        )}

        {/* Declarer crown */}
        {player.is_declarer && (
          <motion.div
            className="absolute -top-3 left-1/2 transform -translate-x-1/2"
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <span className="text-2xl drop-shadow-lg" title="Declarer">
              👑
            </span>
          </motion.div>
        )}

        {/* Partner indicator */}
        {player.is_partner && (
          <motion.div
            className="absolute -top-3 left-1/2 transform -translate-x-1/2"
            initial={{ y: -10, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <span className="text-2xl drop-shadow-lg" title="Partner">
              🤝
            </span>
          </motion.div>
        )}
      </div>

      {/* Player name */}
      <div className="flex flex-col items-center gap-1">
        <div
          className={`
            text-sm font-semibold px-3 py-1 rounded-full
            ${isLocalPlayer ? 'bg-blue-600 text-white' : 'bg-slate-700 text-slate-200'}
            ${isCurrentTurn ? 'ring-2 ring-yellow-400' : ''}
          `}
        >
          {player.name}
          {isLocalPlayer && <span className="ml-1 text-xs opacity-80">(You)</span>}
        </div>

        {/* Position label */}
        <div className="text-xs text-slate-500">
          {positionLabels[position]}
        </div>
      </div>

      {/* Score (if available) */}
      {player.score !== undefined && player.score !== 0 && (
        <div className="bg-slate-800 px-3 py-1 rounded-lg">
          <span className="text-xs text-slate-400">Score: </span>
          <span className={`text-sm font-bold ${player.score > 0 ? 'text-green-400' : 'text-red-400'}`}>
            {player.score > 0 ? '+' : ''}{player.score}
          </span>
        </div>
      )}
    </motion.div>
  )
}
