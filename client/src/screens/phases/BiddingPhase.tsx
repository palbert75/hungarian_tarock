import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import type { Table } from '@/hooks/useTable'
import { useIsWide } from '@/hooks/useIsWide'
import GameLayout from '@/components/GameLayout'
import Seats from '@/components/Seats'
import { HandGrid } from '@/components/Hand'
import HintBox, { useHint } from '@/components/HintBox'
import type { BidType } from '@/types'

const BID_BUTTONS: BidType[] = ['three', 'two', 'one', 'solo', 'hold', 'pass']

export default function BiddingPhase({ table }: { table: Table }) {
  const { t } = useTranslation()
  const wide = useIsWide()
  const { game, myHand } = table
  const yourTurnData = useGameStore((s) => s.yourTurnData)
  const hint = useHint(yourTurnData?.hint, table.isMyTurn)
  const validBids = table.isMyTurn ? yourTurnData?.valid_bids ?? ['pass'] : []

  const highest = [...game.bid_history].reverse().find((b) => b.bid_type !== 'pass')
  const lastBidOf = (position: number) =>
    [...game.bid_history].reverse().find((b) => b.player_position === position)

  const top = (
    <Seats
      table={table}
      content={(position) => {
        const bid = lastBidOf(position)
        if (bid) {
          const leading = highest && bid === highest
          return (
            <span className={`bubble ${leading ? 'bubble-hi' : ''} ${bid.bid_type === 'pass' ? 'bubble-muted' : ''}`}>
              {t(`bid.${bid.bid_type}`)}
            </span>
          )
        }
        return <span className="bubble bubble-muted">{position === game.current_turn ? '…' : '–'}</span>
      }}
    />
  )

  const actions = (
    <div className="grid grid-cols-3 gap-2">
      {BID_BUTTONS.map((bid) => (
        <button
          key={bid}
          type="button"
          disabled={!validBids.includes(bid)}
          onClick={() => socketManager.placeBid(bid)}
          className={`tap ${bid === 'pass' ? 'tap-pass' : 'tap-blue'} ${hint?.payload.bid_type === bid ? 'tap-hint' : ''}`}
        >
          {t(`bid.${bid}`)}
        </button>
      ))}
    </div>
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
