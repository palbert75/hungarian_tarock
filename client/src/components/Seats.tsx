import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import TableView, { SeatLabel } from './TableView'
import type { Table } from '@/hooks/useTable'
import type { Seat } from '@/types'

interface SeatsProps {
  table: Table
  /** What lies in front of each player (a card, a bid bubble…), by table position */
  content: (position: number) => ReactNode
  /** Extra line under the name, by table position */
  detail?: (position: number) => ReactNode
  /** Seat to highlight as the one to move (defaults to the current turn) */
  turn?: number | null
  big?: boolean
  center?: ReactNode
}

/**
 * The four players around the table with something in front of each.
 * For N the name is above the content; for the others it is below, so the
 * contents of all four meet in the middle like cards on a real table.
 */
export default function Seats({ table, content, detail, turn, big, center }: SeatsProps) {
  const { game, me } = table
  const turnPos = turn === undefined ? game.current_turn : turn
  const seats: Partial<Record<Seat, ReactNode>> = {}

  for (const seat of ['N', 'W', 'E', 'S'] as Seat[]) {
    const position = table.positionAt(seat)
    const player = table.playerAt(position)
    const label = (
      <SeatLabel
        player={player}
        isMe={position === me}
        isTurn={position === turnPos}
        isDealer={position === game.dealer_position}
        isDeclarer={position === game.declarer_position}
        isPartner={game.partner_revealed && position === game.partner_position}
        detail={detail?.(position)}
        small={!big}
      />
    )
    const body = <div className="flex items-center justify-center min-h-[1.5rem]">{content(position)}</div>
    seats[seat] = (
      <div className={`flex flex-col items-center gap-1 max-w-full ${big ? 'p-1' : 'px-1'}`}>
        {seat === 'N' ? (
          <>
            {label}
            {body}
          </>
        ) : (
          <>
            {body}
            {label}
          </>
        )}
      </div>
    )
  }

  return <TableView seats={seats} center={center} big={big} />
}

/** "Waiting for X" / "Your turn" for the top bar. */
export function TurnStatus({ table }: { table: Table }) {
  const { t } = useTranslation()
  if (table.isMyTurn) return <span className="text-yellow-300">{t('game.yourTurn')}</span>
  return <span>{t('game.waitingFor', { name: table.nameAt(table.game.current_turn) })}</span>
}
