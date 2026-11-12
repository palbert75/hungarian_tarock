import type { ReactNode } from 'react'

interface GameLayoutProps {
  /** The table: what the others did */
  top: ReactNode
  /** Tutorial hint (between the table and the hand) */
  hint?: ReactNode
  /** My hand */
  hand: ReactNode
  /** My choices */
  actions?: ReactNode
  /** Which band gets the room: my hand (deciding) or the table (watching) */
  focus: 'hand' | 'table'
  wide?: boolean
}

/**
 * Three bands: small table / big hand / thumb buttons.
 * With focus "table" the table grows and the hand shrinks to a strip.
 * On wide screens the table sits beside the hand and both are large.
 */
export default function GameLayout({ top, hint, hand, actions, focus, wide }: GameLayoutProps) {
  if (wide) {
    return (
      <div className="flex-1 min-h-0 flex gap-4 p-4 max-w-6xl w-full mx-auto">
        <div className="flex-1 min-w-0 min-h-0 rounded-2xl band-top p-3">{top}</div>
        <div className="flex-1 min-w-0 min-h-0 flex flex-col gap-3">
          {hint}
          <div className="flex-1 min-h-0">{hand}</div>
          {actions && <div>{actions}</div>}
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 min-h-0 flex flex-col">
      <div className={`band-top safe-x py-2 ${focus === 'table' ? 'flex-1 min-h-0' : 'flex-none'}`}>{top}</div>
      {hint && <div className="safe-x pt-2 flex-none">{hint}</div>}
      <div className={`safe-x ${focus === 'hand' ? 'flex-1 min-h-0 py-1' : 'flex-none bg-black/25'}`}>{hand}</div>
      {actions && <div className="safe-x safe-bottom pt-2 flex-none">{actions}</div>}
    </div>
  )
}
