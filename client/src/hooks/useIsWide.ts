import { useEffect, useState } from 'react'

const QUERY = '(min-width: 900px) and (min-height: 600px)'

/** True when there is room to show the table and the hand large at the same time. */
export function useIsWide(): boolean {
  const [wide, setWide] = useState(() => window.matchMedia(QUERY).matches)
  useEffect(() => {
    const mq = window.matchMedia(QUERY)
    const onChange = () => setWide(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return wide
}
