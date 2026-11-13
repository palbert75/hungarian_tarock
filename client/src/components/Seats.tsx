import { useEffect, useState, type CSSProperties, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import TableView, { SeatLabel } from './TableView'
import type { Table } from '@/hooks/useTable'
import { useSides, type Relation } from '@/hooks/useSides'
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
 * What I knew about each seat when the table was last drawn. Kept outside the
 * component because every phase draws its own table: the sparks must also fly
 * when the news arrives together with a change of phase.
 */
const seen: { hand: string; relations: Record<number, Relation> } = { hand: '', relations: {} }

const SPARKS = Array.from({ length: 14 }, (_, i) => {
  const angle = (i / 14) * Math.PI * 2 + (i % 2) * 0.2
  const reach = 34 + (i % 3) * 14
  return { dx: Math.cos(angle) * reach, dy: Math.sin(angle) * reach, delay: (i % 4) * 35 }
})

/** A short burst of sparks in the seat's new colour. */
function Burst({ relation }: { relation: Relation }) {
  return (
    <span className={`seat-burst burst-${relation}`} aria-hidden="true">
      <b />
      {SPARKS.map((s, i) => (
        <i key={i} style={{ '--dx': `${s.dx}px`, '--dy': `${s.dy}px`, '--delay': `${s.delay}ms` } as CSSProperties} />
      ))}
    </span>
  )
}

/**
 * The four players around the table with something in front of each.
 * For N the name is above the content; for the others it is below, so the
 * contents of all four meet in the middle like cards on a real table.
 */
export default function Seats({ table, content, detail, turn, big, center }: SeatsProps) {
  const { game, me } = table
  const turnPos = turn === undefined ? game.current_turn : turn
  const { relationOf, known } = useSides(table)
  const seats: Partial<Record<Seat, ReactNode>> = {}

  // Sparks on a seat whose side has just come to light
  const [bursts, setBursts] = useState<Record<number, { id: number; relation: Relation }>>({})
  const hand = `${game.game_id}/${game.hand_number ?? 0}`
  const relations = [0, 1, 2, 3].map((p) => (known ? relationOf(p) : 'unknown'))
  const relationKey = relations.join(',')
  useEffect(() => {
    const fresh = seen.hand !== hand
    const revealed: Record<number, { id: number; relation: Relation }> = {}
    relations.forEach((relation, position) => {
      const before = fresh ? undefined : seen.relations[position]
      if (before === 'unknown' && relation !== 'unknown' && position !== me) {
        revealed[position] = { id: Date.now() + position, relation }
      }
      seen.relations[position] = relation
    })
    seen.hand = hand
    if (!Object.keys(revealed).length) return
    setBursts((old) => ({ ...old, ...revealed }))
    const timer = setTimeout(() => setBursts({}), 1300)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hand, relationKey])

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
        side={known ? relationOf(position) : undefined}
        detail={detail?.(position)}
        small={!big}
      />
    )
    const body = <div className="flex items-center justify-center min-h-[1.5rem]">{content(position)}</div>
    seats[seat] = (
      <div
        data-seat-pos={position}
        className={`seat-box ${known ? `seat-${relationOf(position)}` : ''} flex flex-col items-center gap-1 max-w-full ${big ? 'p-1.5' : 'px-1 py-0.5'}`}
      >
        {bursts[position] && <Burst key={bursts[position].id} relation={bursts[position].relation} />}
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

/** A small key to the seat colours: who plays with whom. */
export function SideLegend({ table }: { table: Table }) {
  const { t } = useTranslation()
  const { relationOf, known } = useSides(table)
  if (!known) return null
  const all = [0, 1, 2, 3].map(relationOf)
  return (
    <span className="inline-flex items-center gap-2 align-middle">
      <span className="side-pill side-ally">{t('side.ally')}</span>
      {all.includes('enemy') && <span className="side-pill side-enemy">{t('side.enemy')}</span>}
      {all.includes('unknown') && <span className="side-pill side-unknown">{t('side.unknown')}</span>}
    </span>
  )
}

/** "Waiting for X" / "Your turn" for the top bar. */
export function TurnStatus({ table }: { table: Table }) {
  const { t } = useTranslation()
  if (table.isMyTurn) return <span className="text-yellow-300">{t('game.yourTurn')}</span>
  return <span>{t('game.waitingFor', { name: table.nameAt(table.game.current_turn) })}</span>
}
