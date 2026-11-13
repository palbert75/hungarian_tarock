import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { deviceLanguage, useSettings } from '@/store/settingsStore'
import { useInstall } from '@/hooks/useInstall'
import { DONATE_URL } from '@/utils/donate'

/** First visit: who are you? */
export default function ConnectionScreen() {
  const { t } = useTranslation()
  const setPlayerName = useGameStore((s) => s.setPlayerName)
  const invited = useGameStore((s) => !!s.pendingRoomId)
  const language = useSettings((s) => s.language) ?? deviceLanguage()
  const setLanguage = useSettings((s) => s.setLanguage)
  const { state: installState, install } = useInstall()
  const [name, setName] = useState('')
  const clean = name.trim().slice(0, 20)

  return (
    <div className="h-full game-felt text-white overflow-y-auto">
      <form
        className="min-h-full max-w-sm mx-auto safe-x safe-top safe-bottom flex flex-col justify-center gap-5 py-8"
        onSubmit={(e) => {
          e.preventDefault()
          if (clean.length >= 2) setPlayerName(clean)
        }}
      >
        <div className="text-center">
          <div className="text-5xl">🃏</div>
          <h1 className="mt-2 text-3xl font-bold">Tarokk</h1>
          <p className="mt-1 text-sm text-slate-300">{invited ? t('welcome.invited') : t('welcome.subtitle')}</p>
        </div>
        <label className="flex flex-col gap-1.5 text-sm text-slate-200">
          {t('welcome.name')}
          <input
            className="input-field text-lg"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('welcome.namePlaceholder')}
            maxLength={20}
            autoComplete="nickname"
            autoFocus
          />
        </label>
        <button type="submit" className="tap tap-go w-full" disabled={clean.length < 2}>
          {t('welcome.go')}
        </button>
        <div className="flex justify-center gap-2">
          {(['hu', 'en'] as const).map((lng) => (
            <button
              key={lng}
              type="button"
              className={`chip ${language === lng ? 'chip-on' : ''}`}
              onClick={() => setLanguage(lng)}
            >
              {lng === 'hu' ? 'Magyar' : 'English'}
            </button>
          ))}
        </div>
        {(installState === 'prompt' || installState === 'ios' || DONATE_URL) && (
          <div className="flex flex-col items-center gap-2 pt-2 text-xs text-slate-300">
            {installState === 'prompt' && (
              <button type="button" className="chip" onClick={() => install()}>
                ⬇︎ {t('settings.installGo')}
              </button>
            )}
            {installState === 'ios' && <p className="text-center">{t('settings.installIos')}</p>}
            {DONATE_URL && (
              <a className="chip" href={DONATE_URL} target="_blank" rel="noopener noreferrer">
                ☕ {t('settings.donate')}
              </a>
            )}
          </div>
        )}
      </form>
    </div>
  )
}
