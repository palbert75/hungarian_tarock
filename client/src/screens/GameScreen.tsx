import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { socketManager } from '@/services/socketManager'
import { useTable, type Table } from '@/hooks/useTable'
import TopBar from '@/components/TopBar'
import SettingsSheet from '@/components/SettingsSheet'
import ChatSheet from '@/components/Chat'
import ReportSheet from '@/components/ReportSheet'
import { SideLegend, TurnStatus } from '@/components/Seats'
import { tarokkName } from '@/utils/cardNames'
import BiddingPhase from './phases/BiddingPhase'
import DiscardingPhase from './phases/DiscardingPhase'
import PartnerCallPhase from './phases/PartnerCallPhase'
import AnnouncementsPhase from './phases/AnnouncementsPhase'
import PlayingPhase from './phases/PlayingPhase'
import GameOverScreen from './GameOverScreen'

/** One line saying what is being played: who bid what, the called card, what was announced. */
function ContractLine({ table }: { table: Table }) {
  const { t } = useTranslation()
  const { game } = table
  if (game.declarer_position === null || !game.winning_bid || game.phase === 'bidding') return null
  const parts = [`${table.nameAt(game.declarer_position)}: ${t(`bid.${game.winning_bid.bid_type}`)}`]
  if (game.called_card_rank) parts.push(t('game.called', { card: tarokkName(game.called_card_rank, t) }))
  if (game.required_call && game.invit) parts.push(`${t('bidding.invit', { card: game.invit.card })} (${table.nameAt(game.invit.by)})`)
  else if (game.required_call && game.yielded_by !== null && game.yielded_by !== undefined) {
    parts.push(`${t('bidding.yielded')} (${table.nameAt(game.yielded_by)})`)
  }
  if (game.declarer_alone) parts.push(t('game.alone'))
  if (game.game_contra) parts.push(t('announce.contraGame'))
  for (const a of game.announcements) {
    const mark = a.recontra ? ` (${t('announce.recontraShort')})` : a.contra ? ` (${t('announce.contraShort')})` : ''
    parts.push(`${t(`announcement.${a.announcement_type}`)}${mark}`)
  }
  return (
    <div className="flex-none safe-x py-1 text-center text-[0.72rem] text-slate-200/90 bg-black/25">
      <div className="truncate">{parts.join(' · ')}</div>
      <div className="pt-0.5 text-[0.65rem]">
        <SideLegend table={table} />
      </div>
    </div>
  )
}

/** The table owner may hand a dropped player's seat to a bot. */
function DroppedBar({ table }: { table: Table }) {
  const { t } = useTranslation()
  const dropped = table.game.players.filter((p) => !p.is_connected && !p.is_bot && !p.bot_controlled && !p.vacant)
  if (!dropped.length) return null
  return (
    <div className="flex-none safe-x py-1.5 bg-red-950/80 border-b border-red-400/30 flex flex-col gap-1">
      {dropped.map((p) => (
        <div key={p.id} className="flex items-center justify-between gap-2 text-xs text-red-100">
          <span className="truncate">{t('game.dropped', { name: p.name })}</span>
          {table.isOwner ? (
            <button
              type="button"
              className="chip !min-h-0 !py-1 flex-none"
              onClick={() => socketManager.replaceWithBot(p.position)}
            >
              🤖 {t('game.replaceWithBot')}
            </button>
          ) : (
            <span className="flex-none opacity-80">{t('game.ownerCanReplace')}</span>
          )}
        </div>
      ))}
    </div>
  )
}

function Phase({ table }: { table: Table }) {
  const { t } = useTranslation()
  switch (table.game.phase) {
    case 'bidding':
      return <BiddingPhase table={table} />
    case 'discarding':
      return <DiscardingPhase table={table} />
    case 'partner_call':
      return <PartnerCallPhase table={table} />
    case 'announcements':
      return <AnnouncementsPhase table={table} />
    case 'playing':
      return <PlayingPhase table={table} />
    case 'scoring':
    case 'game_end':
      return <GameOverScreen table={table} />
    default:
      return <div className="flex-1 flex items-center justify-center text-slate-200">{t('game.dealing')}</div>
  }
}

export default function GameScreen() {
  const { t } = useTranslation()
  const table = useTable()
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)

  const over = table?.game.phase === 'game_end' || table?.game.phase === 'scoring'

  return (
    <div className="h-full flex flex-col game-felt text-white">
      <TopBar
        left={table ? t('game.hand', { number: table.game.hand_number ?? 1 }) : null}
        status={table ? over ? t('over.title') : <TurnStatus table={table} /> : null}
        onSettings={() => setSettingsOpen(true)}
        onChat={() => setChatOpen(true)}
        onReport={table ? () => setReportOpen(true) : undefined}
      />
      {table ? (
        <>
          {!over && <ContractLine table={table} />}
          <DroppedBar table={table} />
          <Phase table={table} />
        </>
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-200">{t('game.dealing')}</div>
      )}
      <SettingsSheet open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <ReportSheet open={reportOpen} onClose={() => setReportOpen(false)} />
      <ChatSheet open={chatOpen} onClose={() => setChatOpen(false)} />
    </div>
  )
}
