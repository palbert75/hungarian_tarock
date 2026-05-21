import { useState, useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'

type InfoDialog = 'settings' | 'rules' | 'about' | null

export default function ConnectionScreen() {
  const [name, setName] = useState('')
  const [isConnecting, setIsConnecting] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [infoDialog, setInfoDialog] = useState<InfoDialog>(null)
  const reconnectionAttempted = useRef(false)
  const connectionStatus = useGameStore((state) => state.connectionStatus)
  const addToast = useGameStore((state) => state.addToast)
  const playerId = useGameStore((state) => state.playerId)
  const playerName = useGameStore((state) => state.playerName)
  const roomState = useGameStore((state) => state.roomState)

  // Attempt to reconnect to previous session on mount (only once)
  useEffect(() => {
    // Prevent multiple reconnection attempts
    if (reconnectionAttempted.current) return

    const attemptReconnection = async () => {
      // Check if we have persisted data for reconnection
      if (playerId && playerName && roomState?.room_id) {
        console.log('[ConnectionScreen] Found persisted session, attempting reconnection...')
        console.log('[ConnectionScreen] Player ID:', playerId)
        console.log('[ConnectionScreen] Player Name:', playerName)
        console.log('[ConnectionScreen] Room ID:', roomState.room_id)

        reconnectionAttempted.current = true
        setIsReconnecting(true)

        try {
          // First connect to the server
          await socketManager.connect(playerName)

          // Then try to rejoin the previous room
          const reconnected = socketManager.reconnectToGame()

          if (reconnected) {
            console.log('[ConnectionScreen] Reconnection initiated successfully')
            addToast({
              type: 'success',
              message: 'Reconnecting to your game...',
              duration: 2000,
            })
          } else {
            console.log('[ConnectionScreen] Reconnection failed - insufficient data')
            setIsReconnecting(false)
          }
        } catch (error) {
          console.error('[ConnectionScreen] Reconnection error:', error)
          setIsReconnecting(false)
          addToast({
            type: 'warning',
            message: 'Could not reconnect to previous game',
            duration: 3000,
          })
        }
      } else {
        console.log('[ConnectionScreen] No persisted session found')
      }
    }

    attemptReconnection()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount

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

  const dialogContent = {
    settings: {
      title: 'Settings',
      body: (
        <div className="space-y-4 text-sm text-slate-300">
          <div className="rounded-lg border border-slate-600/50 bg-slate-950/40 p-4">
            <div className="font-semibold text-white">Server</div>
            <div className="mt-1 text-slate-400">The client connects to the configured Socket.IO game server.</div>
          </div>
          <div className="rounded-lg border border-slate-600/50 bg-slate-950/40 p-4">
            <div className="font-semibold text-white">Session recovery</div>
            <div className="mt-1 text-slate-400">Player and room data are kept locally so you can reconnect to an active game.</div>
          </div>
        </div>
      ),
    },
    rules: {
      title: 'Rules',
      body: (
        <div className="space-y-3 text-sm text-slate-300">
          <p>Hungarian Tarokk is a four-player trick-taking game using a 42-card deck.</p>
          <p>Players bid for the contract, take cards from the talon, discard back to nine cards, call a partner, make announcements, then play nine tricks.</p>
          <p>Follow suit when possible. Tarokk cards are trumps. Announcements such as Trull, Four Kings, Volat, Pagat Ultimo, and XXI Catch can increase the score.</p>
        </div>
      ),
    },
    about: {
      title: 'About',
      body: (
        <div className="space-y-3 text-sm text-slate-300">
          <p>Hungarian Tarokk is an online multiplayer card game with real-time rooms, chat, persistence, and reconnect support.</p>
          <p>This client is built with React, Vite, Tailwind CSS, Framer Motion, Zustand, and Socket.IO.</p>
          <p>Created by <span className="font-semibold text-white">Albert Papp</span>.</p>
          <a
            href="https://github.com/palbert75/hungarian_tarock"
            target="_blank"
            rel="noreferrer"
            className="inline-flex text-blue-300 underline-offset-4 hover:text-blue-200 hover:underline"
          >
            github.com/palbert75/hungarian_tarock
          </a>
          <p className="text-slate-500">Version 0.1.0</p>
        </div>
      ),
    },
  }

  return (
    <div className="screen-scroll app-backdrop p-4 md:p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-auto flex min-h-full w-full max-w-md flex-col justify-center py-8"
      >
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2 }}
          className="text-center mb-8 md:mb-12"
        >
          <h1 className="font-display text-5xl md:text-6xl font-bold text-gradient mb-4">
            Hungarian Tarokk
          </h1>
          <p className="text-slate-300 text-lg">
            Online Multiplayer Card Game
          </p>
        </motion.div>

        {/* Connection Form */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="glass-panel rounded-xl p-8"
        >
          {isReconnecting ? (
            // Show reconnection status
            <div className="text-center py-4">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                className="mx-auto mb-5 h-12 w-12 rounded-full border-4 border-slate-600 border-t-blue-300"
              />
              <h3 className="text-white font-semibold text-xl mb-2">
                Reconnecting to your game...
              </h3>
              <p className="text-slate-400 text-sm">
                Please wait while we restore your session
              </p>
            </div>
          ) : (
            // Show normal connection form
            <>
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
                  className="input-field disabled:opacity-50 disabled:cursor-not-allowed"
                  autoFocus
                />
              </div>

              <button
                onClick={handleConnect}
                disabled={isConnecting || !name.trim() || name.trim().length < 2}
                className="btn btn-primary w-full py-3 px-6 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isConnecting ? (
                  <span className="flex items-center justify-center gap-2">
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
            </>
          )}
        </motion.div>

        {/* Footer Links */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-8 text-center flex items-center justify-center gap-4"
        >
          <button
            onClick={() => setInfoDialog('settings')}
            className="text-slate-400 hover:text-white transition-colors text-sm"
          >
            Settings
          </button>
          <button
            onClick={() => setInfoDialog('rules')}
            className="text-slate-400 hover:text-white transition-colors text-sm"
          >
            Rules
          </button>
          <button
            onClick={() => setInfoDialog('about')}
            className="text-slate-400 hover:text-white transition-colors text-sm"
          >
            About
          </button>
        </motion.div>

        {/* Version */}
        <div className="mt-8 text-center text-slate-500 text-xs">
          v0.1.0 • Open Source
        </div>
      </motion.div>

      <AnimatePresence>
        {infoDialog && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 md:items-center"
            onClick={() => setInfoDialog(null)}
          >
            <motion.div
              initial={{ opacity: 0, y: 16, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 16, scale: 0.96 }}
              className="glass-panel w-full max-w-lg rounded-xl p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-5 flex items-center justify-between gap-4">
                <h2 className="text-2xl font-bold text-white">{dialogContent[infoDialog].title}</h2>
                <button
                  onClick={() => setInfoDialog(null)}
                  className="btn btn-muted min-h-0 px-3 py-2 text-sm"
                  aria-label="Close dialog"
                >
                  Close
                </button>
              </div>
              {dialogContent[infoDialog].body}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
