import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import TopBar from '@/components/TopBar'
import SettingsSheet from '@/components/SettingsSheet'

/** Pick a table, start one, or play against bots straight away. */
export default function LobbyScreen() {
  const { t } = useTranslation()
  const playerName = useGameStore((s) => s.playerName)
  const setPlayerName = useGameStore((s) => s.setPlayerName)
  const rooms = useGameStore((s) => s.availableRooms)
  const online = useGameStore((s) => s.connectionStatus === 'connected')
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [code, setCode] = useState('')

  // Keep the list fresh while the lobby is open
  useEffect(() => {
    if (!online) return
    socketManager.listRooms()
    const timer = setInterval(() => socketManager.listRooms(), 4000)
    return () => clearInterval(timer)
  }, [online])

  return (
    <div className="h-full flex flex-col game-felt text-white">
      <TopBar
        left={
          <button type="button" className="underline decoration-dotted truncate" onClick={() => setPlayerName('')}>
            {playerName} ✎
          </button>
        }
        status="Tarokk"
        onSettings={() => setSettingsOpen(true)}
      />

      <div className="flex-1 min-h-0 overflow-y-auto safe-x py-3">
        <div className="max-w-xl mx-auto flex flex-col gap-3">
          <button type="button" className="tap tap-go w-full" disabled={!online} onClick={() => socketManager.createRoom(true)}>
            🤖 {t('lobby.playBots')}
          </button>
          <button type="button" className="tap tap-blue w-full" disabled={!online} onClick={() => socketManager.createRoom(false)}>
            ＋ {t('lobby.newTable')}
          </button>

          <h2 className="mt-2 text-xs uppercase tracking-wide text-slate-300">{t('lobby.openTables')}</h2>
          {rooms.length === 0 && (
            <p className="rounded-2xl bg-black/25 p-4 text-center text-sm text-slate-300">{t('lobby.noTables')}</p>
          )}
          {rooms.map((room) => (
            <button
              key={room.room_id}
              type="button"
              disabled={!online}
              onClick={() => socketManager.joinRoom(room.room_id)}
              className="rounded-2xl bg-black/25 border border-white/10 p-3 flex items-center gap-3 text-left active:scale-[0.99]"
            >
              <div className="min-w-0 flex-1">
                <div className="truncate font-semibold">
                  {room.players.map((p) => (p.is_bot ? `🤖 ${p.name}` : p.name)).join(', ') || t('lobby.emptyTable')}
                </div>
                <div className="text-xs text-slate-300">
                  {t('lobby.seats', { taken: room.players.length })}
                  {room.phase === 'game_end' ? ` · ${t('lobby.betweenHands')}` : ''}
                </div>
              </div>
              <span className="chip chip-on flex-none">{t('lobby.join')}</span>
            </button>
          ))}

          <h2 className="mt-2 text-xs uppercase tracking-wide text-slate-300">{t('lobby.haveCode')}</h2>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              if (code.trim()) socketManager.joinRoom(code.trim())
            }}
          >
            <input
              className="input-field flex-1 min-w-0"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={t('lobby.codePlaceholder')}
              autoCapitalize="none"
              autoCorrect="off"
            />
            <button type="submit" className="tap tap-ghost flex-none px-5" disabled={!online || !code.trim()}>
              {t('lobby.join')}
            </button>
          </form>
        </div>
      </div>

      <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
