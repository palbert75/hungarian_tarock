import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import type { RecentReport } from '@/types'

const STATUS_STYLE: Record<RecentReport['status'], { key: string; className: string }> = {
  fixed: { key: 'lobby.statusFixed', className: 'bg-emerald-500/25 text-emerald-200 border-emerald-400/40' },
  wont_fix: { key: 'lobby.statusWontFix', className: 'bg-slate-500/25 text-slate-200 border-slate-400/40' },
  open: { key: 'lobby.statusOpen', className: 'bg-amber-500/20 text-amber-200 border-amber-400/40' },
}

/** The thank-you board: who sent the latest problem reports, and what became of each. */
export default function ThanksBoard() {
  const { t, i18n } = useTranslation()
  const reports = useGameStore((s) => s.recentReports)
  const online = useGameStore((s) => s.connectionStatus === 'connected')

  useEffect(() => {
    if (online) socketManager.listRecentReports()
  }, [online])

  if (reports.length === 0) return null

  const lang = i18n.language?.startsWith('hu') ? 'hu' : 'en'
  // Contributors, most reports first
  const counts = new Map<string, number>()
  for (const r of reports) counts.set(r.name, (counts.get(r.name) ?? 0) + 1)
  const contributors = [...counts.entries()].sort((a, b) => b[1] - a[1])
  const date = new Intl.DateTimeFormat(lang === 'hu' ? 'hu-HU' : 'en-GB', { month: 'short', day: 'numeric' })

  return (
    <section className="mt-2 flex flex-col gap-2">
      <h2 className="text-xs uppercase tracking-wide text-slate-300">🙏 {t('lobby.thanksTitle')}</h2>
      <div className="rounded-2xl bg-black/25 border border-white/10 p-3 flex flex-col gap-3">
        <p className="text-sm text-slate-300">{t('lobby.thanksIntro')}</p>
        <div className="flex flex-wrap gap-2">
          {contributors.map(([name, count]) => (
            <span key={name} className="chip chip-on">
              {name} ×{count}
            </span>
          ))}
        </div>
        <ul className="flex flex-col divide-y divide-white/10">
          {reports.map((r) => {
            const status = STATUS_STYLE[r.status] ?? STATUS_STYLE.open
            const note = r.note[lang] ?? r.note.en ?? r.note.hu
            const when = r.created_at ? date.format(new Date(r.created_at)) : ''
            return (
              <li key={r.id} className="py-2 flex items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-sm">
                    <span className="font-semibold">{r.name}</span>
                    {when && <span className="text-xs text-slate-400"> · {when}</span>}
                  </div>
                  {note && <div className="text-xs text-slate-300">{note}</div>}
                </div>
                <span className={`flex-none rounded-full border px-2 py-0.5 text-xs ${status.className}`}>
                  {t(status.key)}
                </span>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}
