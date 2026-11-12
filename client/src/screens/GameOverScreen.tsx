import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import type { Table } from '@/hooks/useTable'
import { shareInvite } from '@/utils/invite'

const signed = (n: number) => (n > 0 ? `+${n}` : `${n}`)

/** Result of the hand, running totals, and the way on: next hand or leave. */
export default function GameOverScreen({ table }: { table: Table }) {
  const { t } = useTranslation()
  const { game, me } = table
  const result = useGameStore((s) => s.gameOverData)
  const room = useGameStore((s) => s.roomState)
  const addToast = useGameStore((s) => s.addToast)

  const seats = [0, 1, 2, 3].map((position) => ({
    position,
    seated: room?.players.find((p) => p.position === position),
  }))
  const meInRoom = room?.players.find((p) => p.position === me)
  const iAmReady = !!meInRoom?.ready_next
  const freeSeats = seats.filter((s) => !s.seated).length

  const declarerTeam = new Set<number>()
  if (result) {
    declarerTeam.add(result.declarer)
    if (result.partner !== null && result.partner !== undefined) declarerTeam.add(result.partner)
  }
  const iWon = result ? (result.winner === 'declarer_team') === declarerTeam.has(me) : false
  const handDelta = (position: number) => (result ? (result.player_scores[String(position)] ?? 50) - 50 : 0)
  const total = (position: number) =>
    seats[position].seated?.total_score ?? result?.total_scores?.[position] ?? game.players[position]?.total_score ?? 0

  const role = (position: number) => {
    if (!result) return ''
    if (position === result.declarer) return t('seat.declarer')
    if (declarerTeam.has(position)) return t('seat.partner')
    return ''
  }

  const share = async () => {
    if (!room) return
    const outcome = await shareInvite(room.room_id, t('invite.text'))
    if (outcome === 'copied') addToast({ type: 'success', message: t('invite.copied') })
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto safe-x py-3">
        <div className="max-w-xl mx-auto flex flex-col gap-3">
          {result && (
            <div className={`rounded-2xl p-4 text-center border ${iWon ? 'bg-green-900/50 border-green-400/40' : 'bg-red-950/50 border-red-400/30'}`}>
              <div className="text-2xl font-bold">{iWon ? t('over.youWon') : t('over.youLost')}</div>
              <div className="mt-1 text-sm text-slate-200">
                {result.winner === 'declarer_team' ? t('over.declarerWon') : t('over.defendersWon')}
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                <div className="rounded-xl bg-black/25 p-2">
                  <div className="text-xs text-slate-300">{t('over.declarerSide')}</div>
                  <div className="text-xl font-bold">{result.declarer_team_points}</div>
                </div>
                <div className="rounded-xl bg-black/25 p-2">
                  <div className="text-xs text-slate-300">{t('over.defenderSide')}</div>
                  <div className="text-xl font-bold">{result.opponent_team_points}</div>
                </div>
              </div>
              <div className="mt-2 text-xs text-slate-300">
                {t('over.gameValue', { value: result.final_game_value })}
                {result.game_contra ? ` · ${t('announce.contraGame')}` : ''}
                {result.declarer_alone ? ` · ${t('game.alone')}` : ''}
              </div>
            </div>
          )}

          {result && result.announcement_details.length > 0 && (
            <div className="rounded-2xl bg-black/25 p-3 text-sm">
              <div className="text-xs uppercase tracking-wide text-slate-300 mb-1.5">{t('over.bonuses')}</div>
              {result.announcement_details.map((a, i) => (
                <div key={i} className="flex justify-between gap-2 py-0.5">
                  <span className="truncate">
                    {a.achieved ? '✓' : '✗'} {t(`announcement.${a.type}`)}
                    {!a.announced ? ` (${t('over.silent')})` : ''}
                    {a.recontra ? ` · ${t('announce.recontraShort')}` : a.contra ? ` · ${t('announce.contraShort')}` : ''}
                    <span className="text-slate-300">
                      {' – '}
                      {a.announced
                        ? table.nameAt(a.player_position)
                        : declarerTeam.has(a.player_position)
                          ? t('over.declarerSide')
                          : t('over.defenderSide')}
                    </span>
                  </span>
                  <span className="flex-none font-semibold">
                    {a.type === 'double_game' || a.type === 'volat'
                      ? a.achieved && a.multiplier
                        ? `×${a.multiplier}`
                        : '–'
                      : signed(a.points)}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="rounded-2xl bg-black/25 p-3">
            <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 gap-y-1.5 items-center text-sm">
              <div className="text-xs uppercase tracking-wide text-slate-300">{t('over.player')}</div>
              <div className="text-xs uppercase tracking-wide text-slate-300 text-right">{t('over.thisHand')}</div>
              <div className="text-xs uppercase tracking-wide text-slate-300 text-right">{t('over.total')}</div>
              {seats.map(({ position, seated }) => {
                const delta = handDelta(position)
                return (
                  <div key={position} className="contents">
                    <div className="min-w-0 flex items-center gap-1.5">
                      <span className="truncate font-semibold">
                        {seated ? (
                          <>
                            {seated.is_bot || seated.bot_controlled ? '🤖 ' : ''}
                            {seated.name}
                            {position === me ? ` (${t('seat.you')})` : ''}
                          </>
                        ) : (
                          <span className="text-slate-400">{t('over.freeSeat')}</span>
                        )}
                      </span>
                      {role(position) && <span className="text-[0.65rem] text-yellow-300 flex-none">{role(position)}</span>}
                      {seated && !seated.is_bot && !seated.bot_controlled && seated.ready_next && (
                        <span className="text-green-400 flex-none">✓</span>
                      )}
                      {!seated && table.isOwner && (
                        <button
                          type="button"
                          className="chip !min-h-0 !py-0.5 flex-none"
                          onClick={() => socketManager.addBot(position)}
                        >
                          🤖 {t('room.addBot')}
                        </button>
                      )}
                    </div>
                    <div className={`text-right font-semibold ${delta > 0 ? 'text-green-400' : delta < 0 ? 'text-red-400' : ''}`}>
                      {result ? signed(delta) : '–'}
                    </div>
                    <div className="text-right font-bold">{signed(total(position))}</div>
                  </div>
                )
              })}
            </div>
          </div>

          {freeSeats > 0 && <p className="text-center text-xs text-slate-300">{t('over.needFour')}</p>}
        </div>
      </div>

      <div className="flex-none safe-x safe-bottom pt-2">
        <div className="max-w-xl mx-auto flex flex-col gap-2">
          {freeSeats > 0 && (
            <button type="button" className="tap tap-ghost w-full" onClick={share}>
              {t('invite.share')}
            </button>
          )}
          <div className="grid grid-cols-[1fr_2fr] gap-2">
            <button type="button" className="tap tap-ghost" onClick={() => socketManager.leaveRoom()}>
              {t('over.leave')}
            </button>
            <button type="button" className="tap tap-go" disabled={iAmReady} onClick={() => socketManager.nextHand()}>
              {iAmReady ? t('over.waitingOthers') : t('over.nextHand')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
