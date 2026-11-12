import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import Sheet from './Sheet'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'

const formatTime = (timestamp: number) => {
  const d = new Date(timestamp)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}

/** Table chat in a sheet. */
export default function ChatSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')
  const endRef = useRef<HTMLDivElement>(null)
  const chatMessages = useGameStore((s) => s.chatMessages)
  const playerName = useGameStore((s) => s.playerName)
  const markChatRead = useGameStore((s) => s.markChatRead)

  useEffect(() => {
    if (open) {
      markChatRead()
      endRef.current?.scrollIntoView({ block: 'end' })
    }
  }, [open, chatMessages, markChatRead])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim()) return
    socketManager.sendChatMessage(message.trim())
    setMessage('')
  }

  return (
    <Sheet open={open} title={t('chat.title')} onClose={onClose} tall>
      <div className="h-full flex flex-col">
        <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2">
          {chatMessages.length === 0 && <p className="text-center text-sm text-slate-400 py-6">{t('chat.empty')}</p>}
          {chatMessages.map((msg) => {
            const own = msg.player_name === playerName
            return (
              <div key={msg.id} className={`flex flex-col ${own ? 'items-end' : 'items-start'}`}>
                <div className={`max-w-[85%] rounded-xl px-3 py-2 ${own ? 'bg-blue-700' : 'bg-slate-700'}`}>
                  {!own && <div className="text-xs font-semibold text-slate-300">{msg.player_name}</div>}
                  <div className="text-sm break-words text-white">{msg.message}</div>
                </div>
                <div className="text-[0.65rem] text-slate-500 px-1">{formatTime(msg.timestamp)}</div>
              </div>
            )
          })}
          <div ref={endRef} />
        </div>
        <form onSubmit={submit} className="flex gap-2 p-3 border-t border-slate-700/70 flex-none">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t('chat.placeholder')}
            maxLength={500}
            className="input-field flex-1 text-base"
          />
          <button type="submit" disabled={!message.trim()} className="tap tap-blue">
            {t('chat.send')}
          </button>
        </form>
      </div>
    </Sheet>
  )
}
