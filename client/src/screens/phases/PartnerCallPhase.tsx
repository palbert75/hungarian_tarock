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
import { tarokkName } from '@/utils/cardNames'

/** Tarokks that can be called, from the XX downwards. */
const CALLABLE = ['XX', 'XIX', 'XVIII', 'XVII', 'XVI']

export default function PartnerCallPhase({ table }: { table: Table }) {
  const { t } = useTranslation()
  const wide = useIsWide()
  const { game, me, myHand } = table
  const yourTurnData = useGameStore((s) => s.yourTurnData)
  const isDeclarer = game.declarer_position === me
  const hint = useHint(yourTurnData?.hint, isDeclarer)

  const held = new Set(myHand.filter((c) => c.suit === 'tarokk').map((c) => c.rank))
  // Normally the XX; a declarer holding it calls the highest tarokk below that they do not hold
  // After an invit or a yielded game the bidding has already chosen the card
  const required = game.required_call || null
  const requiredFrom = game.invit && game.invit.by !== game.declarer_position ? game.invit.by : game.yielded_by
  const usual = required ?? CALLABLE.find((rank) => !held.has(rank)) ?? 'XX'
  const [choice, setChoice] = useState(usual)
  useEffect(() => setChoice(usual), [usual])

  const top = (
    <Seats
      table={table}
      turn={game.declarer_position}
      content={(position) =>
        position === game.declarer_position ? (
          <span className="bubble bubble-hi">{t(`bid.${game.winning_bid?.bid_type ?? 'three'}`)}</span>
        ) : null
      }
    />
  )

  const actions = isDeclarer ? (
    <div className="flex flex-col gap-2">
      <div className="text-center text-xs text-slate-200">
        {required
          ? t('call.required', { card: tarokkName(required, t), name: table.nameAt(requiredFrom ?? 0) })
          : t('call.choose')}
      </div>
      <div className="grid grid-cols-5 gap-1.5">
        {CALLABLE.map((rank) => (
          <button
            key={rank}
            type="button"
            disabled={!!required && rank !== required}
            onClick={() => setChoice(rank)}
            className={`chip !px-1 ${choice === rank ? 'chip-on' : ''} ${hint?.payload.tarokk_rank === rank ? 'tap-hint' : ''}`}
          >
            {tarokkName(rank, t)}
            {held.has(rank) && <span className="ml-0.5 text-[0.6rem] opacity-80">({t('call.yours')})</span>}
          </button>
        ))}
      </div>
      <button type="button" className="tap tap-go w-full" onClick={() => socketManager.callPartner(choice)}>
        {t('call.confirm', { card: tarokkName(choice, t) })}
      </button>
    </div>
  ) : (
    <button type="button" className="tap w-full" disabled>
      {t('call.waiting', { name: table.nameAt(game.declarer_position ?? 0) })}
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
