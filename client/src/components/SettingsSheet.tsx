import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import Sheet from './Sheet'
import { deviceLanguage, useSettings } from '@/store/settingsStore'
import { selectIsOwner, useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import { shareInvite } from '@/utils/invite'
import type { BotSpeed } from '@/types'

function Row({ label, detail, children }: { label: string; detail?: string; children: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-3 border-b border-slate-800">
      <div className="min-w-0">
        <div className="text-sm text-white">{label}</div>
        {detail && <div className="text-xs text-slate-400">{detail}</div>}
      </div>
      <div className="flex-none">{children}</div>
    </div>
  )
}

function Switch({ on, onChange, label }: { on: boolean; onChange: (on: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={() => onChange(!on)}
      className={`relative w-12 h-7 rounded-full transition-colors ${on ? 'bg-green-600' : 'bg-slate-600'}`}
    >
      <span className={`absolute top-0.5 w-6 h-6 rounded-full bg-white transition-all ${on ? 'left-[1.4rem]' : 'left-0.5'}`} />
    </button>
  )
}

function Segments<T extends string>({ value, options, onChange }: {
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="flex rounded-lg border border-slate-600 overflow-hidden text-xs">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`px-3 min-h-[2.25rem] ${o.value === value ? 'bg-blue-800 font-bold text-white' : 'text-slate-300'}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** Settings, reachable from every screen (also mid-game). */
export default function SettingsSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const settings = useSettings()
  const roomState = useGameStore((s) => s.roomState)
  const isOwner = useGameStore(selectIsOwner)
  const addToast = useGameStore((s) => s.addToast)
  const language = settings.language ?? deviceLanguage()

  const leave = () => {
    if (roomState?.game_started && !window.confirm(t('settings.leaveConfirm'))) return
    socketManager.leaveRoom()
    onClose()
  }

  const share = async () => {
    if (!roomState) return
    const result = await shareInvite(roomState.room_id, t('invite.text'))
    if (result === 'copied') addToast({ type: 'success', message: t('invite.copied') })
  }

  return (
    <Sheet open={open} title={t('settings.title')} onClose={onClose}>
      <div className="px-4 pb-4">
        <Row label={t('settings.tutorial')} detail={t('settings.tutorialDetail')}>
          <Switch on={settings.tutorial} onChange={settings.setTutorial} label={t('settings.tutorial')} />
        </Row>
        <Row label={t('settings.language')}>
          <Segments
            value={language}
            onChange={settings.setLanguage}
            options={[
              { value: 'hu', label: 'Magyar' },
              { value: 'en', label: 'English' },
            ]}
          />
        </Row>
        <Row label={t('settings.sound')}>
          <Switch on={settings.sound} onChange={settings.setSound} label={t('settings.sound')} />
        </Row>
        {roomState && (
          <Row label={t('settings.botSpeed')} detail={isOwner ? t('settings.botSpeedDetail') : t('settings.ownerOnly')}>
            {isOwner ? (
              <Segments<BotSpeed>
                value={roomState.bot_speed || 'normal'}
                onChange={(speed) => socketManager.setBotSpeed(speed)}
                options={[
                  { value: 'fast', label: t('settings.fast') },
                  { value: 'normal', label: t('settings.normal') },
                  { value: 'slow', label: t('settings.slow') },
                ]}
              />
            ) : (
              <span className="text-xs text-slate-300">{t(`settings.${roomState.bot_speed || 'normal'}`)}</span>
            )}
          </Row>
        )}
        {roomState && (
          <div className="grid grid-cols-2 gap-2 pt-4">
            <button type="button" className="tap tap-ghost text-sm" onClick={share}>
              🔗 {t('invite.share')}
            </button>
            <button type="button" className="tap tap-pass text-sm" onClick={leave}>
              {t('settings.leave')}
            </button>
          </div>
        )}
      </div>
    </Sheet>
  )
}
