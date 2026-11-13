import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import type { Card, Hint } from '@/types'
import { useSettings } from '@/store/settingsStore'
import { cardShortName, tarokkName } from '@/utils/cardNames'

/** Hearts and diamonds in a text ("♥D", "♦10") in red, as on the cards. */
function colourSuits(text: string): ReactNode[] {
  return text.split(/([♥♦][^\s,.;:!?)]*)/).map((part, i) =>
    i % 2 ? (
      <span key={i} className="suit-red">
        {part}
      </span>
    ) : (
      part
    ),
  )
}

/** The hint to show, or undefined when the tutorial is off or there is none. */
export function useHint(hint: Hint | undefined, isMyTurn: boolean): Hint | undefined {
  const tutorial = useSettings((s) => s.tutorial)
  return tutorial && isMyTurn ? hint : undefined
}

/**
 * Tutorial hint: what a careful player would do here, and why.
 * The server sends a reason key with raw parameters; cards, bids and
 * announcements among them are turned into display names here.
 */
export default function HintBox({ hint, hand = [] }: { hint?: Hint; hand?: Card[] }) {
  const { t } = useTranslation()
  if (!hint) return null

  const byId = new Map(hand.map((c) => [c.id, c]))
  const params: Record<string, unknown> = {}
  for (const [key, value] of Object.entries(hint.reason_params || {})) {
    if (key === 'card' || key.endsWith('_card')) {
      const card = byId.get(String(value))
      params[key] = card ? cardShortName(card, t) : String(value)
    } else if (key === 'cards') {
      params[key] = (value as string[]).map((id) => (byId.get(id) ? cardShortName(byId.get(id)!, t) : id)).join(', ')
    } else if (key === 'rank' || key.endsWith('_rank')) {
      params[key] = tarokkName(String(value), t)
    } else if (key === 'bid') {
      params[key] = t(`bid.${value}`)
    } else if (key === 'announcement') {
      params[key] = t(`announcement.${value}`)
    } else if (key === 'suit') {
      params[key] = t(`suit.${value}`)
    } else {
      params[key] = value
    }
  }

  return (
    <div className="hint-box" role="note">
      <span aria-hidden>💡 </span>
      {colourSuits(t(hint.reason_key, { ...params, defaultValue: t('hint.fallback') }))}
    </div>
  )
}
