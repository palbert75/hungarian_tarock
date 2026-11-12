import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import { takeInviteFromUrl } from '@/utils/invite'
import ConnectionScreen from '@/screens/ConnectionScreen'
import LobbyScreen from '@/screens/LobbyScreen'
import WaitingRoomScreen from '@/screens/WaitingRoomScreen'
import GameScreen from '@/screens/GameScreen'
import Toast from '@/components/Toast'
import ConnectionBanner from '@/components/ConnectionBanner'

// An invite link (?room=…) is remembered before anything else happens
const invited = takeInviteFromUrl()
if (invited) {
  const state = useGameStore.getState()
  // An invite to another table replaces the seat we remembered
  if (state.roomId && state.roomId !== invited) state.resetRoomSession()
  state.setPendingRoomId(invited)
}

function Screen() {
  const { t } = useTranslation()
  const playerName = useGameStore((s) => s.playerName)
  const roomId = useGameStore((s) => s.roomId)
  const pendingRoomId = useGameStore((s) => s.pendingRoomId)
  const roomState = useGameStore((s) => s.roomState)
  const gameState = useGameStore((s) => s.gameState)

  if (!playerName) return <ConnectionScreen />
  if (roomState && !roomState.game_started) return <WaitingRoomScreen />
  if (roomState && gameState) return <GameScreen />
  if (roomState || roomId || pendingRoomId) {
    // On the way back to our seat
    return (
      <div className="h-full flex items-center justify-center game-felt text-slate-200">
        {t('connection.returning')}
      </div>
    )
  }
  return <LobbyScreen />
}

export default function App() {
  const playerName = useGameStore((s) => s.playerName)

  // Online from the moment we have a name; the connection repairs itself
  useEffect(() => {
    if (playerName && !socketManager.isStarted()) socketManager.connect()
  }, [playerName])

  return (
    <div className="w-full h-full">
      <Screen />
      <ConnectionBanner />
      <Toast />
    </div>
  )
}
