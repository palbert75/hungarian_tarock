import type { ReactNode } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'

interface SheetProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  /** Fill the height (chat) instead of fitting the content */
  tall?: boolean
}

/** A panel that slides up from the bottom on phones and sits centred on wide screens. */
export default function Sheet({ open, title, onClose, children, tall }: SheetProps) {
  const { t } = useTranslation()
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-40 sheet-backdrop flex items-end sm:items-center justify-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
        >
          <motion.div
            role="dialog"
            aria-label={title}
            className={`sheet w-full sm:max-w-md flex flex-col safe-bottom ${tall ? 'h-[75dvh]' : ''}`}
            initial={{ y: 40 }}
            animate={{ y: 0 }}
            exit={{ y: 40 }}
            transition={{ duration: 0.18 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700/70 flex-none">
              <h2 className="text-base font-bold text-white">{title}</h2>
              <button type="button" className="tap tap-ghost !min-h-[2.25rem] !py-1 text-sm" onClick={onClose}>
                {t('common.close')}
              </button>
            </div>
            <div className="flex-1 min-h-0 overflow-y-auto">{children}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
