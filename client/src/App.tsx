import { useEffect } from 'react'
import { useGameStore } from '@/store/gameStore'
import ConnectionScreen from '@/screens/ConnectionScreen'
import LobbyScreen from '@/screens/LobbyScreen'
import WaitingRoomScreen from '@/screens/WaitingRoomScreen'
import GameScreen from '@/screens/GameScreen'
import Toast from '@/components/Toast'

function App() {
  const connectionStatus = useGameStore((state) => state.connectionStatus)
  const roomState = useGameStore((state) => state.roomState)
  const gameState = useGameStore((state) => state.gameState)

  // Determine which screen to show
  const getCurrentScreen = () => {
    // Not connected? Show connection screen
    if (connectionStatus !== 'connected') {
      return <ConnectionScreen />
    }

    // Connected but no room? Show lobby
    if (!roomState) {
      return <LobbyScreen />
    }

    // In room, game not started? Show waiting room
    if (roomState && !roomState.game_started) {
      return <WaitingRoomScreen />
    }

    // Game started? Show game screen
    if (roomState?.game_started && gameState) {
      return <GameScreen />
    }

    // Fallback
    return <LobbyScreen />
  }

  // Handle page visibility changes
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        console.log('[App] Tab hidden')
      } else {
        console.log('[App] Tab visible')
        // Could trigger a state refresh here
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  // Handle beforeunload (warn before closing)
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (roomState && roomState.game_started) {
        e.preventDefault()
        e.returnValue = 'Game in progress. Are you sure you want to leave?'
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
    }
  }, [roomState])

  return (
    <div className="w-full h-full bg-slate-900">
      {getCurrentScreen()}
      <Toast />
    </div>
  )
}

export default App
