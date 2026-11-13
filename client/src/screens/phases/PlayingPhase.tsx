import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useGameStore } from '@/store/gameStore'
import { socketManager } from '@/services/socketManager'
import type { Table } from '@/hooks/useTable'
import { useIsWide } from '@/hooks/useIsWide'
import GameLayout from '@/components/GameLayout'
import Seats from '@/components/Seats'
import Card, { CardSlot } from '@/components/Card'
import { HandGrid, HandStrip } from '@/components/Hand'
import HintBox, { useHint } from '@/components/HintBox'
import Sheet from '@/components/Sheet'
import { cardShortName } from '@/utils/cardNames'
import type { Card as CardType, TrickCard } from '@/types'

/** Cards I may play now: follow suit, else tarokk, else anything. */
export function legalCardIds(hand: CardType[], trick: TrickCard[]): string[] {
  if (trick.length === 0 || trick.length >= 4) return hand.map((c) => c.id)
  const lead = trick[0].card.suit
  const sameSuit = hand.filter((c) => c.suit === lead)
  if (sameSuit.length) return sameSuit.map((c) => c.id)
  const tarokks = hand.filter((c) => c.suit === 'tarokk')
  return (tarokks.length ? tarokks : hand).map((c) => c.id)
}

export default function PlayingPhase({ table }: { table: Table }) {
  const { t } = useTranslation()
  const wide = useIsWide()
  const { game, myHand } = table
  const selectedCards = useGameStore((s) => s.selectedCards)
  const toggleCardSelection = useGameStore((s) => s.toggleCardSelection)
  const yourTurnData = useGameStore((s) => s.yourTurnData)
  const finishedTrick = useGameStore((s) => s.finishedTrick)
  const [handOpen, setHandOpen] = useState(false)

  // While the finished trick is on show, everybody looks at the table
  const showingFinished = finishedTrick !== null
  const trick = showingFinished ? finishedTrick.cards : game.current_trick
  const choosing = table.isMyTurn && !showingFinished
  const hint = useHint(yourTurnData?.hint, choosing)

  useEffect(() => {
    if (choosing) setHandOpen(false)
  }, [choosing])

  const legal = choosing ? yourTurnData?.valid_cards ?? legalCardIds(myHand, game.current_trick) : []
  const illegal = choosing ? myHand.filter((c) => !legal.includes(c.id)).map((c) => c.id) : []
  const selectedId = selectedCards.length === 1 && legal.includes(selectedCards[0]) ? selectedCards[0] : null
  const selectedCard = myHand.find((c) => c.id === selectedId)

  const cardAt = (position: number) => trick.find((tc) => tc.player_position === position)?.card
  const miniWidth = '2.2rem'
  const bigWidth = wide ? '5.5rem' : 'clamp(3.2rem, 19vw, 5.2rem)'
  const useBig = wide || !choosing
  const cardWidth = useBig ? bigWidth : miniWidth

  const tableView = (
    <Seats
      table={table}
      big={useBig}
      turn={showingFinished ? finishedTrick.winner : game.current_turn}
      detail={(position) => t('play.tricks', { count: table.playerAt(position)?.tricks_won_count ?? 0 })}
      content={(position) => {
        const card = cardAt(position)
        if (card) {
          return <Card card={card} width={cardWidth} winner={showingFinished && finishedTrick.winner === position} />
        }
        // An empty place for whoever still has to play
        return position === game.current_turn && !showingFinished ? <CardSlot width={cardWidth} /> : (
          <div style={{ width: cardWidth, aspectRatio: '5 / 8' }} />
        )
      }}
      center={
        showingFinished ? (
          <span className="bubble bubble-hi">{t('play.tookTrick', { name: table.nameAt(finishedTrick.winner) })}</span>
        ) : undefined
      }
    />
  )

  const play = () => {
    if (selectedId) socketManager.playCard(selectedId)
  }

  const handGrid = (
    <HandGrid
      cards={myHand}
      selected={selectedId ? [selectedId] : []}
      disabled={illegal}
      hinted={hint?.payload.card_id ? [hint.payload.card_id] : []}
      onTap={choosing ? (id) => toggleCardSelection(id, 1) : undefined}
      onSwipeUp={choosing ? (id) => legal.includes(id) && socketManager.playCard(id) : undefined}
      swipeDirection={wide ? 'left' : 'up'}
    />
  )

  const hand = useBig && !wide ? (
    <HandStrip cards={myHand} onTap={() => setHandOpen(true)} label={t('play.yourHandTap')} />
  ) : (
    handGrid
  )

  const actions = choosing ? (
    <div className="flex flex-col gap-1">
      {illegal.length > 0 && <p className="text-center text-[0.72rem] text-slate-300/80">{t('play.greyedCards')}</p>}
      <button type="button" className="tap tap-go w-full" disabled={!selectedCard} onClick={play}>
        {selectedCard ? t('play.playCard', { card: cardShortName(selectedCard, t) }) : t(wide ? 'play.selectCardWide' : 'play.selectCard')}
      </button>
    </div>
  ) : wide ? (
    <button type="button" className="tap w-full" disabled>
      {t('game.waitingFor', { name: table.nameAt(showingFinished ? finishedTrick.winner : game.current_turn) })}
    </button>
  ) : undefined

  return (
    <>
      <GameLayout
        wide={wide}
        focus={choosing ? 'hand' : 'table'}
        top={tableView}
        hint={<HintBox hint={hint} hand={myHand} />}
        hand={hand}
        actions={actions}
      />
      <Sheet open={handOpen && !wide} title={t('play.yourHand')} onClose={() => setHandOpen(false)}>
        <div className="h-[52dvh] p-2" onClick={() => setHandOpen(false)}>
          <HandGrid cards={myHand} />
        </div>
      </Sheet>
    </>
  )
}
