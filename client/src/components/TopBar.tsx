import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'

interface TopBarProps {
  left?: ReactNode
  /** What is going on right now ("Your turn", "Waiting for Dóra") */
  status?: ReactNode
  onSettings: () => void
  onChat?: () => void
  /** Report a problem with the hand being played */
  onReport?: () => void
}

/** Thin bar on top of every screen: where we are, whose turn, chat and settings. */
export default function TopBar({ left, status, onSettings, onChat, onReport }: TopBarProps) {
  const { t } = useTranslation()
  const unread = useGameStore((s) => s.unreadChat)
  return (
    <header className="flex-none safe-top bg-black/40 border-b border-white/10">
      <div className="safe-x h-11 flex items-center justify-between gap-2 text-sm">
        <div className="min-w-0 flex-1 truncate text-slate-200">{left}</div>
        <div className="min-w-0 flex-[2] text-center truncate font-semibold text-white">{status}</div>
        <div className="flex-none flex items-center justify-end">
          {onReport && (
            <button
              type="button"
              onClick={onReport}
              aria-label={t('report.title')}
              title={t('report.title')}
              className="w-10 h-11 flex items-center justify-center text-lg"
            >
              🐞
            </button>
          )}
          {onChat && (
            <button
              type="button"
              onClick={onChat}
              aria-label={t('chat.title')}
              className="relative w-10 h-11 flex items-center justify-center text-lg"
            >
              💬
              {unread > 0 && (
                <span className="absolute top-1 right-0 min-w-[1.1rem] h-[1.1rem] px-1 rounded-full bg-red-600 text-[0.65rem] font-bold flex items-center justify-center">
                  {unread}
                </span>
              )}
            </button>
          )}
          <button
            type="button"
            onClick={onSettings}
            aria-label={t('settings.title')}
            className="w-10 h-11 flex items-center justify-center text-lg"
          >
            ⚙︎
          </button>
        </div>
      </div>
    </header>
  )
}
