import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'

const toastColors = {
  success: 'border-green-400/50 bg-green-950/95',
  error: 'border-red-400/50 bg-red-950/95',
  warning: 'border-yellow-400/50 bg-yellow-950/95',
  info: 'border-blue-400/50 bg-slate-900/95',
}

/** Short messages, top centre, out of the way of the hand and the buttons. */
export default function Toast() {
  const toasts = useGameStore((state) => state.toasts)
  const removeToast = useGameStore((state) => state.removeToast)

  return (
    <div
      className="fixed left-0 right-0 z-50 flex flex-col items-center gap-1.5 px-3 pointer-events-none"
      style={{ top: 'calc(env(safe-area-inset-top, 0px) + 3rem)' }}
      aria-live="polite"
    >
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.18 }}
            onClick={() => removeToast(toast.id)}
            className={`${toastColors[toast.type]} pointer-events-auto max-w-[min(92vw,26rem)] rounded-xl border px-3 py-2 text-sm font-medium text-white shadow-xl`}
          >
            {toast.message}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
