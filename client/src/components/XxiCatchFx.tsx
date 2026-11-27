import { useMemo, type CSSProperties } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore, selectMyPosition, XXI_CATCH_MS } from '@/store/gameStore'

const CONFETTI_COLOURS = ['#facc15', '#f472b6', '#60a5fa', '#34d399', '#f87171', '#a78bfa', '#fb923c']

/** Seeded so a redraw does not reshuffle the pieces mid-flight. */
function pieces(count: number, seed: number) {
  let x = Math.floor(seed) % 2147483647 || 1
  const rnd = () => (x = (x * 16807) % 2147483647) / 2147483647
  return Array.from({ length: count }, () => ({
    left: rnd() * 100,
    delay: rnd() * 1400,
    duration: 2200 + rnd() * 1600,
    drift: (rnd() - 0.5) * 160,
    spin: (rnd() > 0.5 ? 1 : -1) * (360 + rnd() * 720),
    size: 6 + rnd() * 7,
    colour: CONFETTI_COLOURS[Math.floor(rnd() * CONFETTI_COLOURS.length)],
  }))
}

/**
 * The XXI has just been caught: confetti over the screen of the skíz and its
 * partner, a grey rain over the screen of the XXI and its partner.
 */
export default function XxiCatchFx() {
  const { t } = useTranslation()
  const caught = useGameStore((s) => s.xxiCatch)
  const me = useGameStore(selectMyPosition)
  const players = useGameStore((s) => s.gameState?.players)

  // Only the players the news is for: the partners of a hidden side get theirs later
  const happy = !!caught && me !== null && caught.winners.includes(me)
  const sad = !!caught && me !== null && caught.losers.includes(me)
  const bits = useMemo(() => (caught ? pieces(happy ? 90 : 60, caught.id) : []), [caught, happy])
  if (!caught || (!happy && !sad)) return null

  const nameAt = (position: number) => players?.find((p) => p.position === position)?.name ?? '?'
  const style = { '--fx-ms': `${XXI_CATCH_MS}ms` } as CSSProperties

  return (
    <div key={caught.id} className={`xxi-fx ${happy ? 'xxi-fx-happy' : 'xxi-fx-sad'}`} style={style} aria-live="polite">
      {happy
        ? bits.map((b, i) => (
            <i
              key={i}
              className="xxi-confetti"
              style={{
                left: `${b.left}%`,
                width: `${b.size}px`,
                height: `${b.size * 0.45}px`,
                background: b.colour,
                animationDelay: `${b.delay}ms`,
                animationDuration: `${b.duration}ms`,
                '--drift': `${b.drift}px`,
                '--spin': `${b.spin}deg`,
              } as CSSProperties}
            />
          ))
        : bits.map((b, i) => (
            <i
              key={i}
              className="xxi-rain"
              style={{ left: `${b.left}%`, animationDelay: `${b.delay}ms`, animationDuration: `${b.duration * 0.4}ms` }}
            />
          ))}
      <div className="xxi-banner" role="status">
        <div className="xxi-banner-icon" aria-hidden="true">{happy ? '🎉' : '🌧️'}</div>
        <div className="xxi-banner-title">{t(happy ? 'xxiCatch.won' : 'xxiCatch.lost')}</div>
        <div className="xxi-banner-line">
          {t('xxiCatch.line', { skiz: nameAt(caught.skiz_position), xxi: nameAt(caught.xxi_position) })}
        </div>
      </div>
    </div>
  )
}
