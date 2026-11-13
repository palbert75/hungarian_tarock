import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { Player, RoomPlayer, Seat } from '@/types'

interface TableViewProps {
  /** What to show at each screen seat */
  seats: Partial<Record<Seat, ReactNode>>
  center?: ReactNode
  big?: boolean
  className?: string
}

/** The table seen from above: N on top, W left, E right, me (S) at the bottom. */
export default function TableView({ seats, center, big, className = '' }: TableViewProps) {
  return (
    <div className={`compass ${big ? 'compass-big' : ''} ${className}`}>
      {(['N', 'W', 'E', 'S'] as Seat[]).map((seat) => (
        <div key={seat} className={`seat-${seat} min-w-0 max-w-full flex flex-col items-center justify-center`}>
          {seats[seat]}
        </div>
      ))}
      {center && <div className="seat-C min-w-0 flex items-center justify-center">{center}</div>}
    </div>
  )
}

interface SeatLabelProps {
  player?: Pick<Player, 'name' | 'is_connected'> & Partial<Pick<Player, 'bot_controlled' | 'is_bot'>> | RoomPlayer
  isMe?: boolean
  isTurn?: boolean
  isDealer?: boolean
  isDeclarer?: boolean
  isPartner?: boolean
  /** Which side the seat is on, as far as the viewer knows; omitted before the bidding ends */
  side?: 'ally' | 'enemy' | 'unknown'
  /** Extra line under the name (tricks won, "ready"…) */
  detail?: ReactNode
  small?: boolean
}

/** A player's name with the badges everybody at the table may know. */
export function SeatLabel({ player, isMe, isTurn, isDealer, isDeclarer, isPartner, side, detail, small }: SeatLabelProps) {
  const { t } = useTranslation()
  if (!player) return null
  const dropped = !player.is_connected && !player.bot_controlled
  return (
    <div className={`max-w-full text-center leading-tight ${small ? 'text-[0.68rem]' : 'text-xs'}`}>
      <div
        className={`flex items-center justify-center gap-1 ${side ? `side-pill side-${side}` : ''} ${
          isTurn ? (side ? 'side-turn font-bold' : 'text-yellow-300 font-bold') : 'text-slate-100'
        }`}
        title={side && side !== 'unknown' ? t(`side.${side}`) : undefined}
      >
        {player.bot_controlled && <span aria-label={t('seat.bot')}>🤖</span>}
        <span className="truncate max-w-[6.5rem]">{isMe ? t('seat.you') : player.name}</span>
        {isDeclarer && <span title={t('seat.declarer')} aria-label={t('seat.declarer')}>👑</span>}
        {isPartner && <span title={t('seat.partner')} aria-label={t('seat.partner')}>🤝</span>}
        {isDealer && <span title={t('seat.dealer')} aria-label={t('seat.dealer')} className="opacity-80">Ⓓ</span>}
      </div>
      {dropped ? (
        <div className="text-red-300 font-semibold">{t('seat.dropped')}</div>
      ) : (
        detail && <div className="text-slate-300/80">{detail}</div>
      )}
    </div>
  )
}
