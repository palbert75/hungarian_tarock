/** The link that brings someone straight to a table. */
export function inviteUrl(roomId: string): string {
  const url = new URL(window.location.href)
  url.search = ''
  url.hash = ''
  url.searchParams.set('room', roomId)
  return url.toString()
}

/** Share the invite with the phone's share sheet, or copy it. */
export async function shareInvite(roomId: string, text: string): Promise<'shared' | 'copied' | 'failed'> {
  const url = inviteUrl(roomId)
  try {
    if (navigator.share) {
      await navigator.share({ title: 'Tarokk', text, url })
      return 'shared'
    }
  } catch (e) {
    // The person closed the share sheet: nothing to do
    if ((e as DOMException)?.name === 'AbortError') return 'failed'
  }
  try {
    await navigator.clipboard.writeText(url)
    return 'copied'
  } catch {
    window.prompt(text, url)
    return 'failed'
  }
}

/** Read `?room=<id>` from the address bar and remove it. */
export function takeInviteFromUrl(): string | null {
  const url = new URL(window.location.href)
  const room = url.searchParams.get('room')
  if (room) {
    url.searchParams.delete('room')
    window.history.replaceState({}, '', url.toString())
  }
  return room
}
