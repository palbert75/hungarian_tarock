import { useEffect, useRef } from 'react'
import { useSettings } from '@/store/settingsStore'

const tracks = [
  `${import.meta.env.BASE_URL}music/slow-swing-card.mp3`,
  `${import.meta.env.BASE_URL}music/slow-swing-card-2.mp3`,
]

export default function BackgroundMusic() {
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    const audio = audioRef.current!
    let track = 0

    const play = () => {
      if (!useSettings.getState().music || !audio.paused) return
      if (!audio.hasAttribute('src')) audio.src = tracks[track]
      // Browsers can block playback until a player interacts with the page.
      void audio.play().catch(() => {})
    }

    const nextTrack = () => {
      if (!useSettings.getState().music) return
      track = (track + 1) % tracks.length
      // Keep the same element so its playback permission carries across tracks.
      audio.src = tracks[track]
      play()
    }

    // Run inside the settings click so enabling music keeps the browser gesture.
    const unsubscribe = useSettings.subscribe((settings, previous) => {
      if (settings.music === previous.music) return
      if (settings.music) play()
      else audio.pause()
    })

    window.addEventListener('click', play)
    window.addEventListener('keydown', play)
    audio.addEventListener('ended', nextTrack)

    return () => {
      unsubscribe()
      window.removeEventListener('click', play)
      window.removeEventListener('keydown', play)
      audio.removeEventListener('ended', nextTrack)
      audio.pause()
      if (audio.hasAttribute('src')) {
        audio.removeAttribute('src')
        audio.load()
      }
    }
  }, [])

  return <audio ref={audioRef} preload="none" />
}
