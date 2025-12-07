import { io, Socket } from 'socket.io-client'
import { useGameStore } from '@/store/gameStore'
import type { GameState, RoomState, YourTurnData } from '@/types'

class SocketManager {
  private socket: Socket | null = null
  private serverUrl: string

  constructor() {
    // @ts-ignore - Vite environment variable
    this.serverUrl = import.meta.env.VITE_SERVER_URL || 'https://tarokk.onbased.cloud/'
  }

  connect(playerName: string): Promise<void> {
    return new Promise((resolve, reject) => {
      useGameStore.getState().setConnectionStatus('connecting')

      console.log('=== Socket.IO Connection Attempt ===')
      console.log('[Socket] Server URL:', this.serverUrl)
      console.log('[Socket] Player Name:', playerName)
      console.log('[Socket] Timestamp:', new Date().toISOString())

      // Check if we have a stored player ID (for reconnection)
      const storedPlayerId = useGameStore.getState().playerId
      if (storedPlayerId) {
        console.log('[Socket] Found stored player ID:', storedPlayerId)
      }

      this.socket = io(this.serverUrl, {
        transports: ['websocket', 'polling'],
        upgrade: true,
        reconnection: true,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        reconnectionAttempts: 5,
        withCredentials: false,
        autoConnect: true,
      })

      console.log('[Socket] Socket.IO client created')
      console.log('[Socket] Client version:', (io as any).version || 'unknown')

      // Detailed connection lifecycle events
      this.socket.io.on('open', () => {
        console.log('[Socket.io.Engine] ✓ Engine opened (underlying connection established)')
      })

      this.socket.io.on('close', (reason) => {
        console.log('[Socket.io.Engine] ✗ Engine closed:', reason)
      })

      this.socket.io.on('error', (error) => {
        console.error('[Socket.io.Engine] Engine error:', error)
      })

      this.socket.io.on('packet', (packet: any) => {
        console.log('[Socket.io.Engine] Packet received:', packet.type, packet.data)
      })

      // @ts-ignore - packetCreate is a valid socket.io internal event
      this.socket.io.on('packetCreate', (packet: any) => {
        console.log('[Socket.io.Engine] Packet created (sending):', packet.type, packet.data)
      })

      // Connection events
      this.socket.on('connect', () => {
        console.log('=== Socket.IO Connected Successfully ===')
        console.log('[Socket] ✓ Socket ID:', this.socket?.id)
        console.log('[Socket] Transport:', this.socket?.io?.engine?.transport?.name)
        console.log('[Socket] Connected at:', new Date().toISOString())
        useGameStore.getState().setConnectionStatus('connected')

        // Store the player name immediately
        // We'll get the actual player ID from the server when we receive room_state after joining a room
        const currentPlayerId = useGameStore.getState().playerId

        if (currentPlayerId) {
          console.log('[Socket] Have stored player ID for reconnection:', currentPlayerId)
          // Reconnection case - keep both ID and name
          useGameStore.getState().setPlayerInfo(currentPlayerId, playerName)
        } else {
          // First time connection - store name (ID will come from server)
          console.log('[Socket] Storing player name:', playerName)
          useGameStore.getState().setPlayerInfo('', playerName)
        }

        resolve()
      })

      this.socket.on('connect_error', (error) => {
        console.error('=== Socket.IO Connection Error ===')
        console.error('[Socket] Error object:', error)
        console.error('[Socket] Error message:', error.message)
        console.error('[Socket] Error type:', (error as any).type)
        console.error('[Socket] Error description:', (error as any).description)
        console.error('[Socket] Error context:', (error as any).context)
        console.error('[Socket] Full error:', JSON.stringify(error, null, 2))
        useGameStore.getState().setConnectionStatus('error')
        useGameStore.getState().addToast({
          type: 'error',
          message: `Connection failed: ${error.message}`,
        })
        reject(error)
      })

      this.socket.on('disconnect', (reason) => {
        console.log('=== Socket.IO Disconnected ===')
        console.log('[Socket] Reason:', reason)
        console.log('[Socket] Disconnected at:', new Date().toISOString())
        useGameStore.getState().setConnectionStatus('disconnected')

        if (reason === 'io server disconnect') {
          console.log('[Socket] Server initiated disconnect, attempting reconnect...')
          this.socket?.connect()
        }
      })

      this.socket.on('error', (error) => {
        console.error('[Socket] Socket error event:', error)
      })

      this.socket.on('reconnect_attempt', (attemptNumber) => {
        console.log('[Socket] Reconnection attempt #', attemptNumber)
      })

      this.socket.on('reconnect_error', (error) => {
        console.error('[Socket] Reconnection error:', error)
      })

      this.socket.on('reconnect_failed', () => {
        console.error('[Socket] Reconnection failed after all attempts')
      })

      this.socket.on('reconnect', (attemptNumber) => {
        console.log('[Socket] Reconnected after', attemptNumber, 'attempts')
        useGameStore.getState().setConnectionStatus('connected')
        useGameStore.getState().addToast({
          type: 'success',
          message: 'Reconnected to server',
        })
      })

      this.socket.on('reconnect_attempt', () => {
        useGameStore.getState().setConnectionStatus('reconnecting')
      })

      // Room events
      this.socket.on('room_state', (data: RoomState) => {
        console.log('[Socket] Room state:', data)
        const currentRoomId = useGameStore.getState().roomState?.room_id

        // If joining a new room or switching rooms, clear chat messages
        // (chat history will be loaded via chat_history event)
        if (!currentRoomId || currentRoomId !== data.room_id) {
          console.log('[Socket] Joining room, clearing local chat (will receive history from server)')
          useGameStore.getState().clearChatMessages()
        }

        useGameStore.getState().setRoomState(data)

        // Find our player info and update store
        const myName = useGameStore.getState().playerName
        const player = data.players.find((p) => p.name === myName)
        if (player) {
          // Update position
          useGameStore.getState().setPlayerPosition(player.position)

          // Update player ID with server's ID (important for reconnection)
          const currentPlayerId = useGameStore.getState().playerId
          if (currentPlayerId !== player.id) {
            console.log('[Socket] Updating player ID from server:', player.id)
            useGameStore.getState().setPlayerInfo(player.id, myName)
          }
        }
      })

      this.socket.on('rooms_list', (data: { rooms: any[] }) => {
        console.log('[Socket] Rooms list:', data)
        useGameStore.getState().setAvailableRooms(data.rooms)
      })

      // Game events
      this.socket.on('game_state', (data: GameState | { message: string }) => {
        console.log('[Socket] Game state received:', data)

        // Check if it's a message (all players passed)
        if ('message' in data && !('phase' in data)) {
          console.log('[Socket] Message:', data.message)
          useGameStore.getState().addToast({
            type: 'warning',
            message: data.message,
            duration: 4000,
          })
          // Clear selected cards
          useGameStore.getState().clearSelectedCards()
          return
        }

        const gameState = data as GameState
        console.log('[Socket] My position:', useGameStore.getState().playerPosition)
        const myPos = useGameStore.getState().playerPosition
        if (myPos !== null && gameState.players[myPos]) {
          console.log('[Socket] My hand:', gameState.players[myPos].hand)
          console.log('[Socket] Hand size:', gameState.players[myPos].hand?.length || 0)
        }

        // Clear selected cards when new hand is dealt
        const currentPhase = useGameStore.getState().gameState?.phase
        if (currentPhase !== gameState.phase && gameState.phase === 'dealing') {
          useGameStore.getState().clearSelectedCards()
        }

        // Show toast when transitioning from dealing to bidding (new hand dealt)
        if (currentPhase === 'dealing' && gameState.phase === 'bidding') {
          useGameStore.getState().addToast({
            type: 'success',
            message: 'New hand dealt! Bidding begins.',
            duration: 2000,
          })
        }

        useGameStore.getState().setGameState(gameState)

        // Keep snapshot of current trick cards (for animation fallback)
        if (gameState.current_trick && gameState.current_trick.length > 0) {
          const validTrick = gameState.current_trick.filter(
            (tc) =>
              tc &&
              typeof tc.player_position === 'number' &&
              tc.card &&
              typeof tc.card === 'object'
          )
          useGameStore.getState().setLastTrickSnapshot(validTrick)
        }
      })

      this.socket.on('game_started', () => {
        console.log('[Socket] *** GAME STARTED ***')

        // Update room state to mark game as started
        const currentRoomState = useGameStore.getState().roomState
        if (currentRoomState) {
          useGameStore.getState().setRoomState({
            ...currentRoomState,
            game_started: true,
          })
          console.log('[Socket] Updated roomState.game_started = true')
        }

        useGameStore.getState().addToast({
          type: 'success',
          message: 'Game started! Good luck!',
        })
      })

      this.socket.on('your_turn', (data: YourTurnData) => {
        console.log('[Socket] Your turn:', data)
        useGameStore.getState().setYourTurnData(data)
        useGameStore.getState().addToast({
          type: 'info',
          message: "It's your turn!",
          duration: 2000,
        })
      })

      // Bidding events
      this.socket.on('bid_placed', (data) => {
        console.log('[Socket] Bid placed:', data)
        const gameState = useGameStore.getState().gameState
        const playerName = gameState?.players[data.player_position]?.name || 'Player'
        const bidType = data.bid_type || 'pass'

        // Format bid display
        const bidDisplay = bidType === 'pass' ? 'Pass' :
                          bidType === 'three' ? 'Three' :
                          bidType === 'two' ? 'Two' :
                          bidType === 'one' ? 'One' :
                          bidType === 'solo' ? 'Solo' :
                          bidType === 'hold' ? 'Hold' : bidType

        useGameStore.getState().addToast({
          type: 'info',
          message: `${playerName} bid: ${bidDisplay}`,
          duration: 2000,
        })
      })

      // Talon events
      this.socket.on('talon_distributed', (data) => {
        console.log('[Socket] Talon distributed:', data)
        useGameStore.getState().addToast({
          type: 'info',
          message: `You received ${data.you_received} cards from talon`,
          duration: 2000,
        })
      })

      // Discard events
      this.socket.on('player_discarded', (data) => {
        console.log('[Socket] Player discarded:', data)
        const gameState = useGameStore.getState().gameState
        const player = gameState?.players[data.player_position]
        const playerName = player?.name || `Player ${data.player_position + 1}`

        // Show notification about discarded cards
        let message = `${playerName} discarded ${data.num_cards} card${data.num_cards !== 1 ? 's' : ''}`
        if (data.tarokks_discarded > 0) {
          message += ` (${data.tarokks_discarded} tarokk${data.tarokks_discarded !== 1 ? 's' : ''})`
        }

        useGameStore.getState().addToast({
          type: 'info',
          message: message,
        })
      })

      // Partner events
      this.socket.on('partner_called', (data) => {
        console.log('[Socket] Partner called:', data)
        useGameStore.getState().addToast({
          type: 'info',
          message: `Partner called: ${data.called_card}`,
        })
      })

      this.socket.on('partner_revealed', (data) => {
        console.log('[Socket] Partner revealed:', data)
        const partnerPosition =
          typeof data.partner_position === 'string'
            ? parseInt(data.partner_position, 10)
            : data.partner_position

        const partnerName =
          useGameStore.getState().gameState?.players.find((p) => p.position === partnerPosition)?.name ||
          useGameStore.getState().roomState?.players.find((p) => p.position === partnerPosition)?.name ||
          (partnerPosition !== undefined && partnerPosition !== null
            ? `Player ${partnerPosition + 1}`
            : 'Unknown Player')
        useGameStore.getState().addToast({
          type: 'success',
          message: `Partner revealed: ${partnerName}!`,
        })
      })

      // Announcement events
      this.socket.on('announcement_made', (data) => {
        console.log('[Socket] Announcement made:', data)
        const playerName = useGameStore
          .getState()
          .gameState?.players[data.player_position]?.name
        const status = data.announced ? 'announced' : 'silent'
        useGameStore.getState().addToast({
          type: 'info',
          message: `${playerName}: ${data.announcement_type} (${status})`,
        })
      })

      this.socket.on('contra_made', (data) => {
        console.log('[Socket] Contra made:', data)
        const playerName = useGameStore
          .getState()
          .gameState?.players[data.player_position]?.name
        useGameStore.getState().addToast({
          type: 'warning',
          message: `${playerName} contra'd ${data.announcement_type}!`,
        })
      })

      this.socket.on('recontra_made', (data) => {
        console.log('[Socket] Recontra made:', data)
        const playerName = useGameStore
          .getState()
          .gameState?.players[data.player_position]?.name
        useGameStore.getState().addToast({
          type: 'warning',
          message: `${playerName} recontra'd ${data.announcement_type}!`,
        })
      })

      this.socket.on('announcements_complete', () => {
        console.log('[Socket] Announcements complete')
        useGameStore.getState().addToast({
          type: 'success',
          message: 'Announcements complete! Starting tricks...',
        })
      })

      // Trick events
      this.socket.on('card_played', (data) => {
        console.log('[Socket] Card played:', data)
        // Keep a live snapshot of the trick so we don't lose the last card before trick_complete
        const snapshot = useGameStore.getState().lastTrickSnapshot || []
        const existingIdx = snapshot.findIndex((tc) => tc.player_position === data.player_position)
        const updatedSnapshot = [...snapshot]
        if (existingIdx >= 0) {
          updatedSnapshot[existingIdx] = { player_position: data.player_position, card: data.card }
        } else {
          updatedSnapshot.push({ player_position: data.player_position, card: data.card })
        }
        useGameStore.getState().setLastTrickSnapshot(updatedSnapshot)
      })

      this.socket.on('trick_started', (data) => {
        console.log('[Socket] Trick started:', data)
        // New trick -> reset snapshot so we only keep current trick cards
        useGameStore.getState().clearLastTrickSnapshot()
      })

      this.socket.on('trick_complete', (data) => {
        console.log('[Socket] ====== TRICK COMPLETE EVENT ======')
        console.log('[Socket] Raw data received:', JSON.stringify(data, null, 2))
        console.log('[Socket] data.winner:', data.winner, 'type:', typeof data.winner)
        console.log('[Socket] data.winner_name:', data.winner_name)
        console.log('[Socket] data.trick_number:', data.trick_number)

        // Normalise winner position (server can theoretically send string/number)
        let winnerPosition =
          data.winner !== undefined && data.winner !== null
            ? typeof data.winner === 'string'
              ? parseInt(data.winner, 10)
              : data.winner
            : null

        // Helper: drop any malformed trick card entries
        const sanitizeTrickCards = (cards: any[]) =>
          (cards || []).filter(
            (tc) =>
              tc &&
              typeof tc.player_position === 'number' &&
              tc.card &&
              typeof tc.card === 'object'
          )

        const latestState = useGameStore.getState().gameState
        const lastTrickFromHistory = latestState?.trick_history?.length
          ? latestState.trick_history.reduce((acc, curr) =>
              acc === null || (curr.trick_number ?? -1) > (acc.trick_number ?? -1) ? curr : acc,
            null as any)
          : null

        // Get trick number (already 1-indexed from server)
        const trickNumber = typeof data.trick_number === 'number'
          ? data.trick_number
          : typeof latestState?.trick_number === 'number'
            ? latestState.trick_number
            : lastTrickFromHistory?.trick_number ?? '?'

        // Capture the current trick cards BEFORE they're cleared by game_state update
        const getTrickCards = (): any[] => {
          const refreshed = useGameStore.getState().gameState
          if (!refreshed) return []

          // 1) Cards currently on the table
          if (refreshed.current_trick && refreshed.current_trick.length > 0) {
            return sanitizeTrickCards(refreshed.current_trick)
          }

          // 2) Last known trick from history (prefer matching trick number, else newest)
          if (refreshed.trick_history && refreshed.trick_history.length > 0) {
            const targetTrickNum = typeof trickNumber === 'number' ? trickNumber : null
            const tricks = refreshed.trick_history
            const matchingTrick = targetTrickNum !== null
              ? tricks.find((t) => t.trick_number === targetTrickNum)
              : null
            const newestTrick =
              matchingTrick ||
              tricks.reduce((acc, curr) =>
                acc === null || (curr.trick_number ?? -1) > (acc.trick_number ?? -1) ? curr : acc,
              null as any)

            if (newestTrick?.cards?.length) {
              return sanitizeTrickCards(newestTrick.cards)
            }
          }

          return []
        }

        // Also consider the live snapshot we captured via card_played events
        const snapshotTrickCards = sanitizeTrickCards(useGameStore.getState().lastTrickSnapshot || [])
        let currentTrickCards = getTrickCards()
        if (snapshotTrickCards.length > currentTrickCards.length) {
          currentTrickCards = snapshotTrickCards
        }

        console.log('[Socket] Current trick cards in state:', currentTrickCards)
        console.log('[Socket] Number of cards:', currentTrickCards.length)

        // If we still don't know winner position, fall back to history or current trick
        if (winnerPosition === null) {
          const historyWinner =
            lastTrickFromHistory && typeof (lastTrickFromHistory as any).winner === 'number'
              ? (lastTrickFromHistory as any).winner
              : null
          if (historyWinner !== null) {
            winnerPosition = historyWinner
          } else if (currentTrickCards.length > 0) {
            winnerPosition = currentTrickCards[0].player_position
          }
        }

        // Helper: resolve winner name robustly (uses latest state on each call)
        const resolveWinnerName = (): string | undefined => {
          const refreshed = useGameStore.getState().gameState
          if (data.winner_name) return data.winner_name
          if (winnerPosition === null) return undefined

          // 1) Look in current game state players by position
          const gsPlayer = refreshed?.players?.find((p) => p.position === winnerPosition)
          if (gsPlayer?.name) return gsPlayer.name

          // 2) Look in trick history (server includes winner_name there)
          const history = refreshed?.trick_history || []
          if (history.length) {
            const targetTrickNum = typeof trickNumber === 'number' ? trickNumber : null
            const matchingTrick = targetTrickNum !== null
              ? history.find((t) => t.trick_number === targetTrickNum)
              : history.reduce((acc, curr) =>
                  acc === null || (curr.trick_number ?? -1) > (acc.trick_number ?? -1) ? curr : acc,
                null as any)
            if (matchingTrick?.winner_name) return matchingTrick.winner_name
          }

          // 3) Look in room state players by position
          const roomPlayer = useGameStore.getState().roomState?.players.find((p) => p.position === winnerPosition)
          if (roomPlayer?.name) return roomPlayer.name

          return undefined
        }

        // Get winner name/position from best available data
        if (winnerPosition === null && lastTrickFromHistory?.winner !== undefined) {
          // Recover winner position from trick history if server omitted it
          console.log('[Socket] Winner position missing; using last trick history entry')
          // @ts-ignore
          winnerPosition = lastTrickFromHistory.winner
        }

        let winnerName = resolveWinnerName()
        if (!winnerName && lastTrickFromHistory?.winner_name) {
          winnerName = lastTrickFromHistory.winner_name
        }

        console.log('[Socket] Final values - winnerName:', winnerName, 'trickNumber:', trickNumber)

        // Find which card index is the winning card
        const winningCardIndex = currentTrickCards.findIndex(
          (tc) => tc.player_position === winnerPosition
        )

        console.log('[Socket] Winning card index:', winningCardIndex)

        const updateAnimation = (cards: any[], name: string, winningIdx: number) => {
          useGameStore.getState().setTrickWinnerAnimation({
            winner_position: winnerPosition!,
            winner_name: name,
            cards: sanitizeTrickCards(cards),
            winning_card_index: winningIdx >= 0 ? winningIdx : 0,
            trick_number: trickNumber
          })
        }

        let toastSent = false
        const sendToast = (nameToUse: string) => {
          if (toastSent) return
          toastSent = true
          const readableTrick = trickNumber === '?' ? 'this trick' : `trick ${trickNumber}`
          const readableName = nameToUse || (winnerPosition !== null ? `Player ${winnerPosition + 1}` : 'Winner')
          const toastMessage = `${readableName} won ${readableTrick}!`
          console.log('[Socket] Toast message:', toastMessage)
          useGameStore.getState().addToast({
            type: 'success',
            message: toastMessage,
          })
        }

        const needsRefresh = currentTrickCards.length < 4 || !winnerName

        // Set up the trick winner animation if we have valid data
        if (currentTrickCards.length > 0 && winnerPosition !== null) {
          console.log('[Socket] ✅ Setting up animation with', currentTrickCards.length, 'cards')
          updateAnimation(
            currentTrickCards,
            winnerName || `Player ${winnerPosition + 1}`,
            winningCardIndex
          )

          // Only refresh if we were missing data (avoids double animations)
          if (needsRefresh) {
            setTimeout(() => {
              const refreshedCards = getTrickCards()
              const refreshedName = resolveWinnerName() || winnerName
              const refreshedWinningIdx =
                refreshedCards.findIndex((tc) => tc.player_position === winnerPosition)

              const shouldUpdateCards = refreshedCards.length > currentTrickCards.length
              const shouldUpdateName = refreshedName && refreshedName !== winnerName

              if (shouldUpdateCards || shouldUpdateName) {
                console.log('[Socket] Updating trick animation with refreshed data', {
                  cards: refreshedCards.length,
                  name: refreshedName
                })
                currentTrickCards = refreshedCards.length ? sanitizeTrickCards(refreshedCards) : currentTrickCards
                winnerName = refreshedName || winnerName
                updateAnimation(
                  currentTrickCards,
                  winnerName || `Player ${winnerPosition + 1}`,
                  refreshedWinningIdx >= 0 ? refreshedWinningIdx : winningCardIndex
                )
              }

              // Send toast once we have the best name we can get
              if (!toastSent) {
                const nameForToast = winnerName || resolveWinnerName()
                if (nameForToast) {
                  sendToast(nameForToast)
                } else {
                  sendToast(`Player ${winnerPosition + 1}`)
                }
              }
            }, 180)
          }

          // If we already have a name now, send toast immediately; otherwise it will send after refresh
          if (winnerName) {
            sendToast(winnerName)
          }

          // Clear the animation after delay + collection (3s preview + ~2s fly)
          setTimeout(() => {
            console.log('[Socket] Clearing animation')
            useGameStore.getState().clearTrickWinnerAnimation()
          }, 6000)
        } else {
          console.log('[Socket] ❌ NOT setting up animation. Cards:', currentTrickCards.length, 'Winner:', data.winner)
          const fallbackName =
            winnerPosition !== null ? resolveWinnerName() || `Player ${winnerPosition + 1}` : 'Unknown Player'
          sendToast(fallbackName)
        }
      })

      // Game over
      this.socket.on('game_over', (data) => {
        console.log('[Socket] Game over:', data)
        useGameStore.getState().setGameOverData(data)
        useGameStore.getState().addToast({
          type: 'success',
          message: `Game over! Winner: ${data.winner}`,
        })
      })

      // Chat events
      this.socket.on('chat_history', (data) => {
        console.log('[Socket] Chat history received:', data.messages?.length || 0, 'messages')
        // Load chat history into store
        if (data.messages && Array.isArray(data.messages)) {
          data.messages.forEach((msg: any) => {
            useGameStore.getState().addChatMessage({
              id: msg.id || Math.random().toString(36).substring(7),
              player_name: msg.player_name,
              message: msg.message,
              timestamp: msg.timestamp || Date.now(),
            })
          })
        }
      })

      this.socket.on('chat_message', (data) => {
        console.log('[Socket] Chat message:', data)
        useGameStore.getState().addChatMessage({
          id: data.id || Math.random().toString(36).substring(7),
          player_name: data.player_name,
          message: data.message,
          timestamp: data.timestamp || Date.now(),
        })
      })

      // Error handling
      this.socket.on('error', (data) => {
        console.error('[Socket] Error:', data)
        useGameStore.getState().addToast({
          type: 'error',
          message: data.data?.message || 'An error occurred',
        })
      })
    })
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  // Emit methods

  listRooms() {
    console.log('[Socket] Requesting room list')
    this.socket?.emit('list_rooms', {})
  }

  joinRoom(roomId?: string) {
    const { playerName, playerId } = useGameStore.getState()
    this.socket?.emit('join_room', {
      player_name: playerName,
      player_id: playerId,
      room_id: roomId || null,
    })
  }

  // Attempt to reconnect to previous game session
  reconnectToGame(): boolean {
    const { playerId, playerName, roomState } = useGameStore.getState()

    console.log('[Socket] Attempting reconnection...', {
      playerId,
      playerName,
      roomId: roomState?.room_id,
    })

    // Check if we have enough info to reconnect
    if (!playerId || !playerName || !roomState?.room_id) {
      console.log('[Socket] Not enough data for reconnection')
      return false
    }

    // Try to rejoin the room
    console.log('[Socket] Reconnecting to room:', roomState.room_id)
    this.joinRoom(roomState.room_id)
    return true
  }

  ready() {
    this.socket?.emit('ready', {})
  }

  placeBid(bidType: string) {
    console.log('[Socket] Placing bid:', bidType)
    this.socket?.emit('place_bid', { bid_type: bidType })
  }

  pass() {
    console.log('[Socket] Passing (bidding)')
    this.socket?.emit('place_bid', { bid_type: 'pass' })
  }

  discardCards(cardIds: string[]) {
    useGameStore.getState().clearSelectedCards()
    this.socket?.emit('discard_cards', { card_ids: cardIds })
  }

  callPartner(tarokkRank: string) {
    this.socket?.emit('call_partner', { tarokk_rank: tarokkRank })
  }

  makeAnnouncement(announcementType: string, announced: boolean) {
    this.socket?.emit('make_announcement', {
      announcement_type: announcementType,
      announced,
    })
  }

  makeAnnouncements(announcementTypes: string[], announced: boolean) {
    this.socket?.emit('make_announcement', {
      announcement_types: announcementTypes,
      announced,
    })
  }

  passAnnouncement() {
    this.socket?.emit('pass_announcement', {})
  }

  contraAnnouncement(announcementType: string) {
    this.socket?.emit('contra_announcement', {
      announcement_type: announcementType,
    })
  }

  recontraAnnouncement(announcementType: string) {
    this.socket?.emit('recontra_announcement', {
      announcement_type: announcementType,
    })
  }

  playCard(cardId: string) {
    useGameStore.getState().clearSelectedCards()
    this.socket?.emit('play_card', { card_id: cardId })
  }

  leaveRoom() {
    this.socket?.emit('leave_room', {})
    useGameStore.getState().setRoomState(null)
    useGameStore.getState().setGameState(null)
  }

  sendChatMessage(message: string) {
    const { playerName } = useGameStore.getState()
    console.log('[Socket] Sending chat message:', message)
    this.socket?.emit('send_chat_message', {
      player_name: playerName,
      message,
    })
  }
}

// Singleton instance
export const socketManager = new SocketManager()
