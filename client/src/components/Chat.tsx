import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'

interface ChatProps {
  className?: string
}

export default function Chat({ className = '' }: ChatProps) {
  const [message, setMessage] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chatMessages = useGameStore((state) => state.chatMessages)
  const playerName = useGameStore((state) => state.playerName)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!message.trim()) return

    // Send message via socket
    socketManager.sendChatMessage(message.trim())

    // Clear input
    setMessage('')
  }

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp)
    const hours = date.getHours().toString().padStart(2, '0')
    const minutes = date.getMinutes().toString().padStart(2, '0')
    return `${hours}:${minutes}`
  }

  return (
    <div className={`flex flex-col bg-gray-900/80 backdrop-blur-sm rounded-lg border border-gray-700 ${className}`}>
      {/* Chat header */}
      <div className="px-4 py-3 border-b border-gray-700">
        <h3 className="text-lg font-semibold text-white">Chat</h3>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        <AnimatePresence initial={false}>
          {chatMessages.map((msg) => {
            const isOwnMessage = msg.player_name === playerName

            return (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
                className={`flex flex-col ${isOwnMessage ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`
                    max-w-[80%] rounded-lg px-3 py-2
                    ${isOwnMessage
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-100'
                    }
                  `}
                >
                  {!isOwnMessage && (
                    <div className="text-xs font-semibold text-gray-300 mb-1">
                      {msg.player_name}
                    </div>
                  )}
                  <div className="text-sm break-words">{msg.message}</div>
                </div>
                <div className="text-xs text-gray-400 mt-1 px-1">
                  {formatTimestamp(msg.timestamp)}
                </div>
              </motion.div>
            )
          })}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-700">
        <div className="flex gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type a message..."
            maxLength={500}
            className="
              flex-1 bg-gray-800 text-white rounded-lg px-4 py-2
              border border-gray-600 focus:border-blue-500 focus:outline-none
              placeholder-gray-400 text-sm
            "
          />
          <button
            type="submit"
            disabled={!message.trim()}
            className="
              px-6 py-2 bg-blue-600 text-white rounded-lg
              hover:bg-blue-700 active:bg-blue-800
              disabled:bg-gray-700 disabled:text-gray-400 disabled:cursor-not-allowed
              transition-colors font-medium text-sm
            "
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}
