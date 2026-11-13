import { useTranslation } from 'react-i18next'
import type { Table } from '@/hooks/useTable'
import type { Card, TrickCard } from '@/types'

const TAROKKS_IN_DECK = 22
const isTarokk = (card: Card) => card.suit === 'tarokk'

/** The tarokks that are gone, and how many the other three can still hold. */
export function countTarokks(table: Table, currentTrick: TrickCard[]) {
  const { game, myHand } = table
  const inHistory = (game.trick_history || []).flatMap((trick) => trick.cards)
  // The trick on show may already be in the history: count each card once
  const seen = new Set<string>()
  for (const tc of [...inHistory, ...currentTrick]) if (isTarokk(tc.card)) seen.add(tc.card.id)
  const played = seen.size
  const discarded = game.players.reduce((sum, p) => sum + (p.tarokks_discarded ?? 0), 0)
  const mine = myHand.filter(isTarokk).length
  return { played, discarded, mine, others: Math.max(0, TAROKKS_IN_DECK - played - discarded - mine) }
}

/** Tutorial aid: counting tarokks is half the game. */
export default function TarokkCounter({ table, currentTrick }: { table: Table; currentTrick: TrickCard[] }) {
  const { t } = useTranslation()
  const { played, discarded, mine, others } = countTarokks(table, currentTrick)
  return (
    <div className="tarokk-counter" role="status">
      <span>
        {t('counter.gone')} <b>{played + discarded}</b>/{TAROKKS_IN_DECK}
      </span>
      <span className="text-slate-300">
        ({t('counter.played', { count: played })}, {t('counter.discarded', { count: discarded })})
      </span>
      <span>
        {t('counter.mine')} <b>{mine}</b>
      </span>
      <span>
        {t('counter.others')} <b>{others}</b>
      </span>
    </div>
  )
}
