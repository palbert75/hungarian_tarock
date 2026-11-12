import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Language = 'hu' | 'en'

interface SettingsStore {
  /** Show a recommended action with a reason in every phase */
  tutorial: boolean
  /** null = follow the device language */
  language: Language | null
  sound: boolean
  setTutorial: (on: boolean) => void
  setLanguage: (language: Language) => void
  setSound: (on: boolean) => void
}

/** Per-device settings, kept in localStorage. */
export const useSettings = create<SettingsStore>()(
  persist(
    (set) => ({
      tutorial: false,
      language: null,
      sound: true,
      setTutorial: (tutorial) => set({ tutorial }),
      setLanguage: (language) => set({ language }),
      setSound: (sound) => set({ sound }),
    }),
    { name: 'tarokk-settings' }
  )
)

export function deviceLanguage(): Language {
  const lang = typeof navigator !== 'undefined' ? navigator.language || '' : ''
  return lang.toLowerCase().startsWith('hu') ? 'hu' : 'en'
}
