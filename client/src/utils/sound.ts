import { useSettings } from '@/store/settingsStore'

type SoundKind = 'turn' | 'card' | 'trick'

let ctx: AudioContext | null = null

const TONES: Record<SoundKind, { freq: number[]; duration: number; type: OscillatorType }> = {
  turn: { freq: [660, 880], duration: 0.12, type: 'sine' },
  card: { freq: [220], duration: 0.05, type: 'triangle' },
  trick: { freq: [523, 659, 784], duration: 0.09, type: 'sine' },
}

/** Short generated sounds; silent when sounds are switched off or audio is unavailable. */
export function playSound(kind: SoundKind): void {
  if (!useSettings.getState().sound) return
  try {
    const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AudioCtx) return
    ctx = ctx || new AudioCtx()
    if (ctx.state === 'suspended') void ctx.resume()
    const tone = TONES[kind]
    tone.freq.forEach((freq, i) => {
      const start = ctx!.currentTime + i * tone.duration
      const osc = ctx!.createOscillator()
      const gain = ctx!.createGain()
      osc.type = tone.type
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.0001, start)
      gain.gain.exponentialRampToValueAtTime(0.08, start + 0.01)
      gain.gain.exponentialRampToValueAtTime(0.0001, start + tone.duration)
      osc.connect(gain).connect(ctx!.destination)
      osc.start(start)
      osc.stop(start + tone.duration + 0.02)
    })
  } catch {
    // Audio is a nicety; never let it break the game
  }
}
