import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import type { Table } from '@/hooks/useTable'
import { useIsWide } from '@/hooks/useIsWide'
import GameLayout from '@/components/GameLayout'
import Seats from '@/components/Seats'
import { HandGrid } from '@/components/Hand'
import HintBox, { useHint } from '@/components/HintBox'
import type { Announcement, AnnouncementType } from '@/types'

const ORDER: AnnouncementType[] = ['trull', 'four_kings', 'double_game', 'volat', 'pagat_ultimo', 'xxi_catch']

type Side = 'declarer' | 'opponent' | 'unknown'

/** Which side a seat is on, as far as I can know it. */
function useSides(table: Table) {
  const { game, me, myHand } = table
  const declarer = game.declarer_position
  const called = (game.called_card_rank || '').toLowerCase()
  const iHoldCalled = !!called && myHand.some((c) => c.suit === 'tarokk' && c.rank.toLowerCase() === called)
  const iAmPartner = (game.partner_revealed && game.partner_position === me) || iHoldCalled
  const mySide: Side = me === declarer || iAmPartner ? 'declarer' : 'opponent'

  const sideOf = (position: number): Side => {
    if (position === me) return mySide
    if (position === declarer) return 'declarer'
    if (game.partner_revealed && position === game.partner_position) return 'declarer'
    if (iAmPartner || game.declarer_alone) return 'opponent'
    return 'unknown'
  }
  return { mySide, sideOf }
}

export default function AnnouncementsPhase({ table }: { table: Table }) {
  const { t } = useTranslation()
  const wide = useIsWide()
  const { game, me, myHand } = table
  const yourTurnData = useGameStore((s) => s.yourTurnData)
  const hint = useHint(yourTurnData?.hint, table.isMyTurn)
  const { mySide, sideOf } = useSides(table)
  const [chosen, setChosen] = useState<AnnouncementType[]>([])

  useEffect(() => {
    if (!table.isMyTurn) setChosen([])
  }, [table.isMyTurn])

  const valid = table.isMyTurn ? yourTurnData?.valid_announcements ?? [] : []
  const options = ORDER.filter((a) => valid.includes(a))
  const hinted = hint?.payload.announcement_types ?? []

  const canContra = (a: Announcement) => !a.contra && a.player_position !== me && sideOf(a.player_position) !== mySide
  const canRecontra = (a: Announcement) =>
    !!a.contra && !a.recontra && (a.player_position === me || sideOf(a.player_position) === mySide)
  const contras = table.isMyTurn ? game.announcements.filter(canContra) : []
  const recontras = table.isMyTurn ? game.announcements.filter(canRecontra) : []

  const lastTurn = (position: number) =>
    [...(game.announcement_turn_log || [])].reverse().find((entry) => entry.position === position)

  const toggle = (a: AnnouncementType) =>
    setChosen((list) => (list.includes(a) ? list.filter((x) => x !== a) : [...list, a]))

  const top = (
    <Seats
      table={table}
      content={(position) => {
        const made = game.announcements.filter((a) => a.player_position === position)
        const kontraGame = game.game_contra && game.game_contra_by === position
        if (made.length || kontraGame) {
          return (
            <div className="flex flex-col items-center gap-0.5">
              {kontraGame && <span className="bubble bubble-hi">{t('announce.contraGame')}</span>}
              {made.map((a) => (
                <span key={a.announcement_type} className="bubble bubble-hi">
                  {t(`announcement.${a.announcement_type}`)}
                  {a.recontra ? ` · ${t('announce.recontraShort')}` : a.contra ? ` · ${t('announce.contraShort')}` : ''}
                </span>
              ))}
            </div>
          )
        }
        const turn = lastTurn(position)
        if (turn) return <span className="bubble bubble-muted">{t('bid.pass')}</span>
        return <span className="bubble bubble-muted">{position === game.current_turn ? '…' : '–'}</span>
      }}
    />
  )

  const actions = table.isMyTurn ? (
    <div className="flex flex-col gap-2">
      {options.length > 0 && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {options.map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => toggle(a)}
              className={`chip ${chosen.includes(a) ? 'chip-on' : ''} ${hinted.includes(a) ? 'tap-hint' : ''}`}
            >
              {chosen.includes(a) ? '✓ ' : ''}
              {t(`announcement.${a}`)}
            </button>
          ))}
        </div>
      )}
      {(contras.length > 0 || recontras.length > 0) && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {contras.map((a) => (
            <button
              key={`c-${a.announcement_type}`}
              type="button"
              className={`chip ${hint?.action === 'contra' && hint.payload.announcement_type === a.announcement_type ? 'tap-hint' : ''}`}
              onClick={() => socketManager.contraAnnouncement(a.announcement_type)}
            >
              {t('announce.contra', { what: t(`announcement.${a.announcement_type}`) })}
            </button>
          ))}
          {recontras.map((a) => (
            <button
              key={`r-${a.announcement_type}`}
              type="button"
              className="chip"
              onClick={() => socketManager.recontraAnnouncement(a.announcement_type)}
            >
              {t('announce.recontra', { what: t(`announcement.${a.announcement_type}`) })}
            </button>
          ))}
        </div>
      )}
      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          className={`tap tap-pass ${hint?.action === 'pass_announcement' ? 'tap-hint' : ''}`}
          onClick={() => socketManager.passAnnouncement()}
        >
          {t('bid.pass')}
        </button>
        <button
          type="button"
          className="tap tap-go"
          disabled={chosen.length === 0}
          onClick={() => {
            socketManager.makeAnnouncements(chosen)
            setChosen([])
          }}
        >
          {chosen.length ? t('announce.confirm', { count: chosen.length }) : t('announce.choose')}
        </button>
      </div>
    </div>
  ) : (
    <button type="button" className="tap w-full" disabled>
      {t('game.waitingFor', { name: table.nameAt(game.current_turn) })}
    </button>
  )

  return (
    <GameLayout
      wide={wide}
      focus="hand"
      top={top}
      hint={<HintBox hint={hint} hand={myHand} />}
      hand={<HandGrid cards={myHand} />}
      actions={actions}
    />
  )
}
