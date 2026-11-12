import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import type { Table } from '@/hooks/useTable'
import { useIsWide } from '@/hooks/useIsWide'
import GameLayout from '@/components/GameLayout'
import Seats from '@/components/Seats'
import Card, { CardSlot } from '@/components/Card'
import { HandGrid } from '@/components/Hand'
import HintBox, { useHint } from '@/components/HintBox'
import { canDiscard } from '@/utils/cardNames'
import { sortCards } from '@/utils/cardSorting'

export default function DiscardingPhase({ table }: { table: Table }) {
  const { t } = useTranslation()
  const wide = useIsWide()
  const { game, me, myHand, myPlayer } = table
  const selectedCards = useGameStore((s) => s.selectedCards)
  const toggleCardSelection = useGameStore((s) => s.toggleCardSelection)
  const yourTurnData = useGameStore((s) => s.yourTurnData)
  const hint = useHint(yourTurnData?.hint, table.isMyTurn)

  const need = Math.max(myHand.length - 9, 0)
  const discarded = game.players_who_discarded || []
  const choosing = table.isMyTurn && need > 0
  const protectedIds = myHand.filter((c) => !canDiscard(c)).map((c) => c.id)
  const chosen = sortCards(myHand.filter((c) => selectedCards.includes(c.id)))
  const slotWidth = '2.2rem'

  const top = choosing ? (
    // My skart so far: tap a card here to take it back
    <div className="flex flex-col items-center gap-1.5 py-1">
      <div className="text-xs text-slate-200">{t('discard.goingToSkart', { count: chosen.length, total: need })}</div>
      <div className="flex gap-2">
        {chosen.map((card) => (
          <Card key={card.id} card={card} width={slotWidth} onClick={() => toggleCardSelection(card.id)} />
        ))}
        {Array.from({ length: need - chosen.length }).map((_, i) => (
          <CardSlot key={i} width={slotWidth} />
        ))}
      </div>
    </div>
  ) : (
    <Seats
      table={table}
      content={(position) =>
        discarded.includes(position) ? (
          <span className="bubble">✓ {t('discard.done')}</span>
        ) : (
          <span className="bubble bubble-muted">{position === game.current_turn ? '…' : '–'}</span>
        )
      }
    />
  )

  const actions = choosing ? (
    <div className="flex flex-col gap-1">
      {protectedIds.length > 0 && <p className="text-center text-[0.72rem] text-slate-300/80">{t('discard.protected')}</p>}
      <button
        type="button"
        className="tap tap-go w-full"
        disabled={chosen.length !== need}
        onClick={() => socketManager.discardCards(chosen.map((c) => c.id))}
      >
        {chosen.length === need
          ? t('discard.confirm', { count: need })
          : t('discard.selectMore', { count: need - chosen.length })}
      </button>
    </div>
  ) : (
    <button type="button" className="tap w-full" disabled>
      {discarded.includes(me)
        ? t('discard.waitingOthers')
        : t('game.waitingFor', { name: table.nameAt(game.current_turn) })}
    </button>
  )

  return (
    <GameLayout
      wide={wide}
      focus="hand"
      top={top}
      hint={<HintBox hint={hint} hand={myHand} />}
      hand={
        <HandGrid
          cards={myHand}
          selected={choosing ? selectedCards : []}
          disabled={choosing ? protectedIds : []}
          tagged={myPlayer.talon_card_ids || []}
          tagLabel={t('discard.new')}
          hinted={hint?.payload.card_ids || []}
          onTap={choosing ? (id) => toggleCardSelection(id, need) : undefined}
        />
      }
      actions={actions}
    />
  )
}
