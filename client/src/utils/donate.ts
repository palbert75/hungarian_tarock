/** Where a supporter is sent (a payment link or a donation page). Empty: the option is hidden. */
export const DONATE_URL: string = (import.meta.env.VITE_DONATE_URL as string | undefined)?.trim() || ''
