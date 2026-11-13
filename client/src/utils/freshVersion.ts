/**
 * Keep an open tab on the newest version of the app.
 *
 * The app shell is cached by a service worker. A new version is only picked
 * up when the browser looks for one, and the page that is already open keeps
 * running the old code. So: look for a new version every few minutes and when
 * the tab comes back to the front, and reload once the new one has taken
 * over. A reload in the middle of a hand brings the player back to the seat.
 */
const CHECK_EVERY_MS = 5 * 60 * 1000

export function keepFresh(): void {
  if (!('serviceWorker' in navigator) || import.meta.env.DEV) return
  const hadController = !!navigator.serviceWorker.controller
  let reloading = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    // The very first install also fires this: nothing to refresh then
    if (!hadController || reloading) return
    reloading = true
    window.location.reload()
  })
  const check = () => {
    navigator.serviceWorker.getRegistration().then((registration) => registration?.update()).catch(() => undefined)
  }
  setInterval(check, CHECK_EVERY_MS)
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') check()
  })
}
