import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'

/** Shown whenever the link to the server is down; the app keeps retrying by itself. */
export default function ConnectionBanner() {
  const { t } = useTranslation()
  const status = useGameStore((s) => s.connectionStatus)
  const hasName = useGameStore((s) => !!s.playerName)
  if (status === 'connected' || !hasName) return null
  return (
    <div
      role="status"
      className="fixed inset-x-0 z-[60] flex justify-center px-3 pointer-events-none"
      style={{ top: 'calc(env(safe-area-inset-top, 0px) + 0.4rem)' }}
    >
      <div className="flex items-center gap-2 rounded-full bg-red-900/95 border border-red-400/60 px-4 py-2 text-sm font-semibold text-white shadow-xl">
        <span className="w-3.5 h-3.5 rounded-full border-2 border-white/40 border-t-white animate-spin" />
        {status === 'connecting' ? t('connection.connecting') : t('connection.reconnecting')}
      </div>
    </div>
  )
}
