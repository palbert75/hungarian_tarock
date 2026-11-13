import { useEffect, useState } from 'react'

/** Chrome's install event (not in the standard DOM types). */
interface InstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

// The event may fire before any component mounts, so it is kept here
let pending: InstallPromptEvent | null = null
const listeners = new Set<() => void>()
const notify = () => listeners.forEach((l) => l())

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault()
    pending = e as InstallPromptEvent
    notify()
  })
  window.addEventListener('appinstalled', () => {
    pending = null
    notify()
  })
}

const isStandalone = () =>
  typeof window !== 'undefined' &&
  (window.matchMedia('(display-mode: standalone)').matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true)

const isIos = () =>
  typeof navigator !== 'undefined' &&
  (/iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1))

/**
 * How this device can install the app:
 *  - 'prompt': the browser offers an install dialog (Android, desktop Chrome/Edge)
 *  - 'ios': Safari has no dialog; the person adds it from the share menu
 *  - 'installed': already running as an app
 *  - 'none': this browser cannot install it
 */
export function useInstall(): { state: 'prompt' | 'ios' | 'installed' | 'none'; install: () => Promise<boolean> } {
  const [, tick] = useState(0)
  useEffect(() => {
    const l = () => tick((n) => n + 1)
    listeners.add(l)
    return () => {
      listeners.delete(l)
    }
  }, [])

  const state = isStandalone() ? 'installed' : pending ? 'prompt' : isIos() ? 'ios' : 'none'
  const install = async () => {
    if (!pending) return false
    const event = pending
    await event.prompt()
    const { outcome } = await event.userChoice
    pending = null
    notify()
    return outcome === 'accepted'
  }
  return { state, install }
}
