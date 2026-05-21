import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'

const toastIcons = {
  success: '✅',
  error: '❌',
  warning: '⚠️',
  info: 'ℹ️',
}

const toastColors = {
  success: 'border-green-400/50 bg-green-950/90',
  error: 'border-red-400/50 bg-red-950/90',
  warning: 'border-yellow-400/50 bg-yellow-950/90',
  info: 'border-blue-400/50 bg-blue-950/90',
}

export default function Toast() {
  const toasts = useGameStore((state) => state.toasts)
  const removeToast = useGameStore((state) => state.removeToast)

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 100, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.8 }}
            transition={{ duration: 0.2 }}
            className={`
              ${toastColors[toast.type]}
              text-white px-4 py-3 rounded-lg shadow-2xl border backdrop-blur-md
              flex items-center gap-3 min-w-[300px] max-w-[400px]
              pointer-events-auto cursor-pointer
            `}
            onClick={() => removeToast(toast.id)}
          >
            <span className="text-xl">{toastIcons[toast.type]}</span>
            <span className="flex-1 text-sm font-medium">{toast.message}</span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                removeToast(toast.id)
              }}
              className="text-white/80 hover:text-white transition-colors"
              aria-label="Close notification"
            >
              ✕
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
