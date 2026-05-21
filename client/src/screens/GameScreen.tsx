import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import PlayerAvatar from '@/components/PlayerAvatar'
import Chat from '@/components/Chat'
import BiddingPhase from './phases/BiddingPhase'
import DiscardingPhase from './phases/DiscardingPhase'
import PartnerCallPhase from './phases/PartnerCallPhase'
import AnnouncementsPhase from './phases/AnnouncementsPhase'
import PlayingPhase from './phases/PlayingPhase'
import GameOverScreen from './GameOverScreen'
import type { Bid } from '@/types'

const getBidColor = (bidType: string): string => {
  switch (bidType) {
    case 'three':
      return 'bg-blue-600'
    case 'two':
      return 'bg-purple-600'
    case 'one':
      return 'bg-orange-600'
    case 'solo':
      return 'bg-red-600'
    case 'hold':
      return 'bg-yellow-600'
    default:
      return 'bg-slate-600'
  }
}

const getBidDisplayName = (bidType: string | null): string => {
  if (!bidType || bidType === 'pass') return 'Pass'
  const bidTypes = [
    { value: 'three', label: 'Three' },
    { value: 'two', label: 'Two' },
    { value: 'one', label: 'One' },
    { value: 'solo', label: 'Solo' },
    { value: 'hold', label: 'Hold' },
  ]
  return bidTypes.find((b) => b.value === bidType)?.label || bidType
}

export default function GameScreen() {
  const [showChat, setShowChat] = useState(false)
  const gameState = useGameStore((state) => state.gameState)
  const playerPosition = useGameStore((state) => state.playerPosition)

  const handleLeaveRoom = () => {
    // Confirm before leaving
    const confirmed = window.confirm('Are you sure you want to leave the room? This will end your game session.')
    if (confirmed) {
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

      console.log('[GameScreen] Left room and cleared session storage')
    }
  }

  if (!gameState || playerPosition === null) {
    return (
      <div className="screen-scroll w-full bg-table-green flex items-center justify-center">
        <div className="text-white text-xl">Loading game...</div>
      </div>
    )
  }

  // Show game over screen if game is complete
  if (gameState.phase === 'game_end') {
    return <GameOverScreen gameState={gameState} playerPosition={playerPosition} />
  }

  // Get player positions relative to local player (always show self at bottom)
  const getRelativePosition = (absolutePosition: number): 0 | 1 | 2 | 3 => {
    return ((absolutePosition - playerPosition + 4) % 4) as 0 | 1 | 2 | 3
  }

  // Map absolute positions to screen positions
  // 0: bottom (self), 1: left, 2: top, 3: right
  const playersByScreenPosition = gameState.players.map((player, idx) => ({
    player,
    absolutePosition: idx,
    screenPosition: getRelativePosition(idx),
  }))

  const bottomPlayer = playersByScreenPosition.find((p) => p.screenPosition === 0)
  const leftPlayer = playersByScreenPosition.find((p) => p.screenPosition === 1)
  const topPlayer = playersByScreenPosition.find((p) => p.screenPosition === 2)
  const rightPlayer = playersByScreenPosition.find((p) => p.screenPosition === 3)

  // Render appropriate phase component
  const renderPhase = () => {
    switch (gameState.phase) {
      case 'bidding':
        return <BiddingPhase gameState={gameState} playerPosition={playerPosition} />
      case 'discarding':
        return <DiscardingPhase gameState={gameState} playerPosition={playerPosition} />
      case 'partner_call':
        return <PartnerCallPhase gameState={gameState} playerPosition={playerPosition} />
      case 'announcements':
        return <AnnouncementsPhase gameState={gameState} playerPosition={playerPosition} />
      case 'playing':
        return <PlayingPhase gameState={gameState} playerPosition={playerPosition} />
      default:
        return null
    }
  }

  const showFullTable =
    gameState.phase === 'playing' ||
    gameState.phase === 'waiting'
  const showPhaseOverlay =
    gameState.phase === 'bidding' ||
    gameState.phase === 'discarding' ||
    gameState.phase === 'partner_call' ||
    gameState.phase === 'announcements'

  return (
    <div className="screen-scroll screen-scroll-x table-felt relative">
      {/* Top Bar */}
      <div className="top-bar sticky top-0 left-0 right-0 px-4 md:px-6 py-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between z-10">
        <div className="flex flex-wrap items-center gap-2 md:gap-3">
          <div className="status-pill text-white">
            <span className="text-amber-300">Room</span> {gameState.game_id.substring(0, 8)}
          </div>
          <div className="status-pill">
            Phase <span className="text-blue-300 font-semibold capitalize">{gameState.phase.replace('_', ' ')}</span>
          </div>
          <div className="status-pill">
            Turn <span className="text-yellow-300 font-semibold">
              {gameState.players[gameState.current_turn]?.name}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowChat(!showChat)}
            className={`btn text-sm ${showChat ? 'btn-primary' : 'btn-muted'}`}
          >
            Chat
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleLeaveRoom}
            className="btn btn-danger text-sm"
          >
            Leave
          </motion.button>
        </div>
      </div>

      {/* Game Table Layout */}
      <div className="relative z-[1] flex min-h-full min-w-[320px] w-full flex-col px-3 pb-8 pt-6 md:px-4">
        {showPhaseOverlay ? (
          /* Phase Overlay (Bidding, Discarding, Announcements) */
          <div className="flex-1 flex flex-col gap-4">
            {/* Show player avatars at top */}
            <div className="screen-scroll-x flex items-start justify-between gap-3 px-2 md:px-8 pt-4 pb-2">
              {/* Left Player */}
              <div>
                {leftPlayer && (
                  <PlayerAvatar
                    player={leftPlayer.player}
                    isCurrentTurn={gameState.current_turn === leftPlayer.absolutePosition}
                    position={leftPlayer.absolutePosition as 0 | 1 | 2 | 3}
                    isLocalPlayer={false}
                  />
                )}
              </div>

              {/* Top Player */}
              <div>
                {topPlayer && (
                  <PlayerAvatar
                    player={topPlayer.player}
                    isCurrentTurn={gameState.current_turn === topPlayer.absolutePosition}
                    position={topPlayer.absolutePosition as 0 | 1 | 2 | 3}
                    isLocalPlayer={false}
                  />
                )}
              </div>

              {/* Right Player */}
              <div>
                {rightPlayer && (
                  <PlayerAvatar
                    player={rightPlayer.player}
                    isCurrentTurn={gameState.current_turn === rightPlayer.absolutePosition}
                    position={rightPlayer.absolutePosition as 0 | 1 | 2 | 3}
                    isLocalPlayer={false}
                  />
                )}
              </div>
            </div>

            {/* Phase Content - Centered below players */}
            <div className="flex-1 flex items-start justify-center px-0 md:items-center md:px-4">
              {renderPhase()}
            </div>
          </div>
        ) : showFullTable ? (
          /* Full Table Layout (Playing Phase) */
          <>
            {/* Top Player */}
            <div className="flex justify-center py-2 md:py-4">
              {topPlayer && (
                <PlayerAvatar
                  player={topPlayer.player}
                  isCurrentTurn={gameState.current_turn === topPlayer.absolutePosition}
                  position={topPlayer.absolutePosition as 0 | 1 | 2 | 3}
                  isLocalPlayer={false}
                />
              )}
            </div>

            {/* Middle Area - Left Player, Center Table, Right Player */}
            <div className="flex-1 flex flex-col items-center justify-between gap-4 px-0 md:flex-row md:gap-6 md:px-8">
              {/* Left Player */}
              <div className="flex items-center">
                {leftPlayer && (
                  <PlayerAvatar
                    player={leftPlayer.player}
                    isCurrentTurn={gameState.current_turn === leftPlayer.absolutePosition}
                    position={leftPlayer.absolutePosition as 0 | 1 | 2 | 3}
                    isLocalPlayer={false}
                  />
                )}
              </div>

              {/* Center - Phase Content */}
              <div className="min-w-0 w-full flex-1 flex items-center justify-center">{renderPhase()}</div>

              {/* Right Player */}
              <div className="flex items-center">
                {rightPlayer && (
                  <PlayerAvatar
                    player={rightPlayer.player}
                    isCurrentTurn={gameState.current_turn === rightPlayer.absolutePosition}
                    position={rightPlayer.absolutePosition as 0 | 1 | 2 | 3}
                    isLocalPlayer={false}
                  />
                )}
              </div>
            </div>

            {/* Bottom - Local Player */}
            <div className="flex flex-col items-center">
              {bottomPlayer && (
                <div className="mb-2">
                  <PlayerAvatar
                    player={bottomPlayer.player}
                    isCurrentTurn={gameState.current_turn === bottomPlayer.absolutePosition}
                    position={bottomPlayer.absolutePosition as 0 | 1 | 2 | 3}
                    isLocalPlayer={true}
                  />
                </div>
              )}
            </div>
          </>
        ) : (
          /* Waiting or Unknown Phase */
          <div className="flex-1 flex items-center justify-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="felt-panel rounded-xl p-8 md:p-12 max-w-2xl text-center"
            >
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Game In Progress</h2>
              <p className="text-slate-300 text-lg">
                Current Phase:{' '}
                <span className="text-blue-400 font-semibold capitalize">{gameState.phase}</span>
              </p>
            </motion.div>
          </div>
        )}
      </div>

      {/* Bid History - Bottom Left Corner (only during bidding phase) */}
      {gameState.phase === 'bidding' && gameState.bid_history.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="glass-panel fixed bottom-4 left-4 rounded-xl p-4 z-20 max-w-[calc(100vw-2rem)] sm:max-w-xs"
        >
          <h3 className="text-white font-semibold mb-3 text-sm flex items-center gap-2">
            Bid History
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-2" style={{ scrollbarWidth: 'thin', scrollbarColor: '#475569 #334155' }}>
            {gameState.bid_history.map((bid: Bid, index: number) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between text-sm gap-3"
              >
                <span className="text-slate-300 truncate">
                  {gameState.players[bid.player_position]?.name}
                </span>
                <span
                  className={`
                    font-semibold px-3 py-1 rounded-lg text-white flex-shrink-0
                    ${
                      bid.bid_type && bid.bid_type !== 'pass'
                        ? getBidColor(bid.bid_type)
                        : 'bg-slate-600 text-slate-300'
                    }
                  `}
                >
                  {getBidDisplayName(bid.bid_type)}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Announcement History - Bottom Left Corner (during announcements and playing phases) */}
      {(gameState.phase === 'announcements' || gameState.phase === 'playing') &&
       gameState.announcements && gameState.announcements.length > 0 && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className="glass-panel fixed bottom-4 left-4 rounded-xl p-4 z-20 max-w-[calc(100vw-2rem)] sm:max-w-xs"
        >
          <h3 className="text-white font-semibold mb-3 text-sm flex items-center gap-2">
            Announcements
          </h3>
          <div className="space-y-2 max-h-64 overflow-y-auto pr-2" style={{ scrollbarWidth: 'thin', scrollbarColor: '#475569 #334155' }}>
            {gameState.announcements.map((announcement: any, index: number) => {
              const announcementTypes = [
                { value: 'trull', label: 'Trull', icon: '🎯' },
                { value: 'four_kings', label: 'Four Kings', icon: '👑' },
                { value: 'double_game', label: 'Double', icon: '2️⃣' },
                { value: 'volat', label: 'Volat', icon: '💯' },
                { value: 'pagat_ultimo', label: 'Pagát Ult.', icon: '🎴' },
                { value: 'xxi_catch', label: 'XXI Catch', icon: '🎣' },
              ]
              const announcementInfo = announcementTypes.find(a => a.value === announcement.announcement_type)

              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-slate-700/50 rounded-lg p-2"
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-slate-300 text-xs truncate">
                      {gameState.players[announcement.player_position]?.name}
                    </span>
                    <div className="flex items-center gap-1">
                      {announcement.announced ? (
                        <span className="text-[10px] bg-yellow-600/80 px-1.5 py-0.5 rounded text-white">📢</span>
                      ) : (
                        <span className="text-[10px] bg-slate-600/80 px-1.5 py-0.5 rounded text-white">🤫</span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1">
                      <span className="text-sm">{announcementInfo?.icon}</span>
                      <span className="text-white text-xs font-semibold">{announcementInfo?.label}</span>
                    </div>
                    <div className="flex flex-col gap-0.5">
                      {announcement.contra && (
                        <span className="text-[9px] bg-red-600 px-1.5 py-0.5 rounded text-white font-semibold">
                          Contra
                        </span>
                      )}
                      {announcement.recontra && (
                        <span className="text-[9px] bg-orange-600 px-1.5 py-0.5 rounded text-white font-semibold">
                          Recontra
                        </span>
                      )}
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </motion.div>
      )}

      {/* Chat Sidebar */}
      <AnimatePresence>
        {showChat && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowChat(false)}
              className="fixed inset-0 bg-black/30 z-30"
            />

            {/* Chat Panel */}
            <motion.div
              initial={{ x: 400 }}
              animate={{ x: 0 }}
              exit={{ x: 400 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed right-0 top-0 bottom-0 z-40 w-full max-w-96"
            >
              <Chat className="h-full shadow-2xl" />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}
