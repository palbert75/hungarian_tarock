import { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { selectIsOwner, selectMyPosition, useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import TopBar from '@/components/TopBar'
import SettingsSheet from '@/components/SettingsSheet'
import ChatSheet from '@/components/Chat'
import TableView from '@/components/TableView'
import { positionAt, SEATS } from '@/utils/seats'
import { shareInvite } from '@/utils/invite'
import type { RoomPlayer, Seat } from '@/types'

/** Seat number under a point on the screen (for dragging players between seats). */
function seatUnder(x: number, y: number): number | null {
  const el = document.elementFromPoint(x, y)?.closest('[data-seat-pos]')
  return el ? Number(el.getAttribute('data-seat-pos')) : null
}

/** Before the first hand: who sits where, bots, invite, ready. */
export default function WaitingRoomScreen() {
  const { t } = useTranslation()
  const room = useGameStore((s) => s.roomState)
  const me = useGameStore(selectMyPosition)
  const isOwner = useGameStore(selectIsOwner)
  const addToast = useGameStore((s) => s.addToast)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  /** Seat picked up (by tap or drag) to be moved */
  const [picked, setPicked] = useState<number | null>(null)
  const [over, setOver] = useState<number | null>(null)
  const drag = useRef<{ from: number; moved: boolean; x: number; y: number } | null>(null)

  if (!room) return null
  const myPos = me ?? 0
  const playerAt = (position: number) => room.players.find((p) => p.position === position)
  const mine = playerAt(myPos)
  const free = 4 - room.players.length
  const owner = room.players.find((p) => p.id === room.owner_id)

  const move = (from: number, to: number) => {
    if (from !== to) socketManager.swapSeats(from, to)
    setPicked(null)
  }

  // Owner only: drag a player onto another seat, or tap one seat and then another
  const seatHandlers = (position: number, player?: RoomPlayer) => {
    if (!isOwner) return {}
    return {
      onPointerDown: (e: React.PointerEvent) => {
        if (!player || (e.target as HTMLElement).closest('button')) return
        drag.current = { from: position, moved: false, x: e.clientX, y: e.clientY }
        ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
      },
      onPointerMove: (e: React.PointerEvent) => {
        const d = drag.current
        if (!d) return
        if (!d.moved && Math.hypot(e.clientX - d.x, e.clientY - d.y) > 10) {
          d.moved = true
          setPicked(d.from)
        }
        if (d.moved) setOver(seatUnder(e.clientX, e.clientY))
      },
      onPointerUp: (e: React.PointerEvent) => {
        const d = drag.current
        drag.current = null
        setOver(null)
        if ((e.target as HTMLElement).closest('button')) return
        if (d?.moved) {
          const target = seatUnder(e.clientX, e.clientY)
          if (target !== null) move(d.from, target)
          else setPicked(null)
          return
        }
        // A tap: pick up, put down, or cancel
        if (picked === null) {
          if (player) setPicked(position)
        } else {
          move(picked, position)
        }
      },
      onPointerCancel: () => {
        drag.current = null
        setOver(null)
        setPicked(null)
      },
    }
  }

  const seats: Partial<Record<Seat, React.ReactNode>> = {}
  for (const seat of SEATS) {
    const position = positionAt(seat, myPos)
    const player = playerAt(position)
    const isBot = !!player?.is_bot
    const away = !!player && !isBot && !player.is_connected
    const highlight = picked === position ? 'ring-2 ring-yellow-400' : over === position || (picked !== null && isOwner) ? 'ring-2 ring-yellow-400/40' : ''
    seats[seat] = (
      <div
        data-seat-pos={position}
        {...seatHandlers(position, player)}
        style={{ touchAction: isOwner ? 'none' : undefined }}
        className={`relative w-[7.2rem] max-w-full min-h-[5.2rem] rounded-2xl border px-2 py-2 flex flex-col items-center justify-center gap-0.5 text-center select-none ${
          player ? 'bg-black/35 border-white/15' : 'bg-black/15 border-dashed border-white/25'
        } ${highlight} ${isOwner && player ? 'cursor-grab' : ''}`}
      >
        {player ? (
          <>
            <div className="text-xl leading-none">{isBot ? '🤖' : away ? '💤' : '🙂'}</div>
            <div className="w-full truncate text-sm font-semibold">
              {player.name}
              {position === myPos ? ` (${t('seat.you')})` : ''}
            </div>
            <div className={`text-[0.7rem] ${away ? 'text-red-300' : player.is_ready || isBot ? 'text-green-400' : 'text-slate-300'}`}>
              {away ? t('seat.dropped') : isBot ? t('seat.bot') : player.is_ready ? `✓ ${t('room.ready')}` : t('room.notReady')}
              {player.id === room.owner_id ? ` · ${t('room.owner')}` : ''}
            </div>
            {isOwner && isBot && (
              <button
                type="button"
                aria-label={t('room.removeBot')}
                className="absolute -top-2 -right-2 w-7 h-7 rounded-full bg-red-800 border border-red-300/60 text-xs font-bold"
                onClick={() => socketManager.removeBot(position)}
              >
                ✕
              </button>
            )}
          </>
        ) : (
          <>
            <div className="text-xs text-slate-300">{t('room.freeSeat')}</div>
            {isOwner && picked === null && (
              <button type="button" className="chip !min-h-0 !py-1" onClick={() => socketManager.addBot(position)}>
                🤖 {t('room.addBot')}
              </button>
            )}
          </>
        )}
      </div>
    )
  }

  const share = async () => {
    const outcome = await shareInvite(room.room_id, t('invite.text'))
    if (outcome === 'copied') addToast({ type: 'success', message: t('invite.copied') })
  }

  return (
    <div className="h-full flex flex-col game-felt text-white">
      <TopBar
        left={t('room.code', { code: room.room_id })}
        status={free > 0 ? t('room.waitingPlayers', { count: free }) : t('room.waitingReady')}
        onSettings={() => setSettingsOpen(true)}
        onChat={() => setChatOpen(true)}
      />

      <div className="flex-1 min-h-0 overflow-y-auto safe-x py-3">
        <div className="max-w-xl mx-auto flex flex-col gap-3">
          <TableView
            seats={seats}
            center={<span className="text-2xl">🃏</span>}
            className="rounded-3xl band-top p-3 min-h-[19rem]"
          />
          <p className="text-center text-xs text-slate-300">
            {isOwner
              ? picked !== null
                ? t('room.pickTarget')
                : t('room.ownerHelp')
              : t('room.guestHelp', { name: owner?.name ?? '' })}
          </p>
        </div>
      </div>

      <div className="flex-none safe-x safe-bottom pt-2">
        <div className="max-w-xl mx-auto flex flex-col gap-2">
          <div className="grid grid-cols-2 gap-2">
            <button type="button" className="tap tap-ghost" onClick={share}>
              🔗 {t('invite.share')}
            </button>
            {isOwner ? (
              <button type="button" className="tap tap-ghost" disabled={free === 0} onClick={() => socketManager.fillBots()}>
                🤖 {t('room.fillBots')}
              </button>
            ) : (
              <button type="button" className="tap tap-ghost" onClick={() => socketManager.leaveRoom()}>
                {t('over.leave')}
              </button>
            )}
          </div>
          <button
            type="button"
            className={`tap w-full ${mine?.is_ready ? 'tap-ghost' : 'tap-go'}`}
            onClick={() => socketManager.ready(!mine?.is_ready)}
          >
            {mine?.is_ready ? (free > 0 ? t('room.readyWaiting') : t('room.readyWaitingOthers')) : t('room.imReady')}
          </button>
        </div>
      </div>

      <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <ChatSheet open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
