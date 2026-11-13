import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import Sheet from './Sheet'
import { socketManager } from '@/services/socketManager'
import { useGameStore } from '@/store/gameStore'
import { useSettings } from '@/store/settingsStore'

type Sent = { id: string; report?: unknown }

/** What the screen looked like, to go with the report. No personal data. */
function clientInfo(tutorial: boolean, language: string) {
  const { gameState, yourTurnData } = useGameStore.getState()
  return {
    language,
    tutorial,
    viewport: `${window.innerWidth}x${window.innerHeight}`,
    user_agent: navigator.userAgent,
    phase: gameState?.phase,
    hint: (yourTurnData as { hint?: unknown } | null)?.hint ?? null,
  }
}

function download(sent: Sent) {
  const blob = new Blob([JSON.stringify(sent.report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `tarokk-report-${sent.id}.json`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** Describe a problem; the server stores the whole table with the text. */
export default function ReportSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t, i18n } = useTranslation()
  const tutorial = useSettings((s) => s.tutorial)
  const addToast = useGameStore((s) => s.addToast)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [failed, setFailed] = useState(false)
  const [sent, setSent] = useState<Sent | null>(null)

  const send = async () => {
    setBusy(true)
    setFailed(false)
    try {
      setSent(await socketManager.reportProblem(text.trim(), clientInfo(tutorial, i18n.language)))
      setText('')
    } catch {
      setFailed(true)
    } finally {
      setBusy(false)
    }
  }

  const copy = async () => {
    if (!sent) return
    try {
      await navigator.clipboard.writeText(sent.id)
      addToast({ type: 'success', message: t('report.copied') })
    } catch {
      // No clipboard: the id is on screen and can be selected by hand
    }
  }

  const close = () => {
    setSent(null)
    setFailed(false)
    onClose()
  }

  return (
    <Sheet open={open} title={t('report.title')} onClose={close}>
      <div className="px-4 py-3 flex flex-col gap-3">
        {sent ? (
          <>
            <div className="text-green-400 font-bold">✓ {t('report.saved')}</div>
            <div className="rounded-xl bg-black/30 p-3 flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="text-xs text-slate-400">{t('report.id')}</div>
                <div className="font-mono text-sm text-white select-all truncate">{sent.id}</div>
              </div>
              <button type="button" className="chip flex-none" onClick={copy}>
                {t('report.copy')}
              </button>
            </div>
            {sent.report ? (
              <button type="button" className="tap tap-ghost text-sm" onClick={() => download(sent)}>
                ⬇︎ {t('report.download')}
              </button>
            ) : (
              <p className="text-xs text-slate-400">{t('report.downloadLater')}</p>
            )}
            <div className="grid grid-cols-2 gap-2">
              <button type="button" className="tap tap-ghost text-sm" onClick={() => setSent(null)}>
                {t('report.another')}
              </button>
              <button type="button" className="tap tap-go text-sm" onClick={close}>
                {t('common.close')}
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="text-sm text-slate-300">{t('report.intro')}</p>
            <textarea
              className="w-full rounded-xl bg-slate-900 border border-slate-600 p-3 text-base text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-400"
              rows={5}
              maxLength={2000}
              value={text}
              placeholder={t('report.placeholder')}
              onChange={(e) => setText(e.target.value)}
            />
            {failed && <p className="text-sm text-red-300">{t('report.failed')}</p>}
            <button type="button" className="tap tap-go" disabled={busy || text.trim().length < 3} onClick={send}>
              {busy ? t('report.sending') : t('report.send')}
            </button>
          </>
        )}
      </div>
    </Sheet>
  )
}
