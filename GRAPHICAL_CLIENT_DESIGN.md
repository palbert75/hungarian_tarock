# Hungarian Tarokk - Graphical Client Design Document

## Table of Contents
1. [Technology Stack Recommendations](#technology-stack-recommendations)
2. [Overall Architecture](#overall-architecture)
3. [Design System & Visual Language](#design-system--visual-language)
4. [Game Stages & Screens](#game-stages--screens)
5. [Component Library](#component-library)
6. [Animations & Transitions](#animations--transitions)
7. [Responsive Design](#responsive-design)
8. [Accessibility](#accessibility)

---

## Technology Stack Recommendations

### Frontend Framework Options

#### Option 1: Web Client (React + TypeScript) ⭐ **RECOMMENDED**
**Pros:**
- Cross-platform (desktop, mobile, tablets)
- Easy deployment (just a URL)
- Rich ecosystem for card games
- Socket.IO client readily available
- Hot reload during development

**Tech Stack:**
```
- React 18+ with TypeScript
- Socket.IO client for real-time communication
- Framer Motion for animations
- Tailwind CSS for styling
- Zustand or Redux for state management
- React Spring for physics-based card animations
```

#### Option 2: Desktop Client (Electron)
**Pros:**
- Native-like experience
- Offline capability
- Better performance for heavy animations

**Cons:**
- Larger bundle size
- Platform-specific builds needed

#### Option 3: Native Mobile (React Native)
**Pros:**
- True native performance
- Touch-optimized

**Cons:**
- Separate codebase from web
- App store submission required

### Recommended: Progressive Web App (PWA)
Best of both worlds - web client that can be installed as an app!

---

## Overall Architecture

```
┌─────────────────────────────────────────────────┐
│            React Application                     │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐    ┌──────────────┐          │
│  │   UI Layer   │    │ Game Canvas  │          │
│  │  (React)     │    │ (SVG/Canvas) │          │
│  └──────┬───────┘    └──────┬───────┘          │
│         │                   │                   │
│  ┌──────┴───────────────────┴───────┐          │
│  │   State Management (Zustand)     │          │
│  └──────┬───────────────────────────┘          │
│         │                                        │
│  ┌──────┴───────────────────────────┐          │
│  │   Socket.IO Client Manager       │          │
│  └──────┬───────────────────────────┘          │
│         │                                        │
└─────────┼────────────────────────────────────────┘
          │
          │ WebSocket
          │
┌─────────┼────────────────────────────────────────┐
│         │  Python Server (Current)               │
│  ┌──────┴───────────────────────────┐           │
│  │   Socket.IO Server (Python)      │           │
│  └──────────────────────────────────┘           │
└────────────────────────────────────────────────┘
```

### State Management Structure

```typescript
interface GameStore {
  // Connection state
  connectionStatus: 'disconnected' | 'connecting' | 'connected'
  playerId: string
  playerName: string

  // Room state
  roomId: string | null
  players: Player[]
  isRoomFull: boolean

  // Game state
  phase: GamePhase
  currentTurn: number
  myPosition: number
  hand: Card[]

  // Phase-specific state
  bidHistory: Bid[]
  declarer: number | null
  announcements: Announcement[]
  currentTrick: Array<{position: number, card: Card}>

  // UI state
  selectedCards: string[]
  hoveredCard: string | null
  showingModal: 'rules' | 'score' | null
}
```

---

## Design System & Visual Language

### Color Palette

```css
/* Primary Colors */
--color-table-green: #1a5f3f;
--color-table-felt: #2a7f5f;
--color-card-back: #8b0000;

/* Suit Colors */
--color-hearts: #dc143c;
--color-diamonds: #dc143c;
--color-spades: #000000;
--color-clubs: #000000;
--color-tarokk: #4169e1;

/* UI Colors */
--color-gold: #ffd700;
--color-silver: #c0c0c0;
--color-bronze: #cd7f32;

/* Semantic Colors */
--color-success: #10b981;
--color-warning: #f59e0b;
--color-error: #ef4444;
--color-info: #3b82f6;

/* Backgrounds */
--color-bg-primary: #1e293b;
--color-bg-secondary: #334155;
--color-bg-elevated: #475569;

/* Text */
--color-text-primary: #f1f5f9;
--color-text-secondary: #cbd5e1;
--color-text-muted: #94a3b8;
```

### Typography

```css
/* Font Families */
--font-primary: 'Inter', system-ui, sans-serif;
--font-display: 'Cinzel', serif; /* For game title */
--font-mono: 'Fira Code', monospace; /* For numbers */

/* Font Sizes */
--text-xs: 0.75rem;   /* 12px */
--text-sm: 0.875rem;  /* 14px */
--text-base: 1rem;    /* 16px */
--text-lg: 1.125rem;  /* 18px */
--text-xl: 1.25rem;   /* 20px */
--text-2xl: 1.5rem;   /* 24px */
--text-3xl: 1.875rem; /* 30px */
--text-4xl: 2.25rem;  /* 36px */
```

### Card Design

```
┌─────────────┐
│ XXI      ⚜️ │  <- Tarokk card
│             │
│      👑     │  <- Central illustration
│             │
│ ⚜️      XXI │
└─────────────┘

┌─────────────┐
│ K        ♥️ │  <- Suit card (King of Hearts)
│             │
│    👑 👑    │  <- Suit-specific illustration
│             │
│ ♥️        K │
└─────────────┘
```

### Animation Principles

1. **Snappy but not jarring** - 200-300ms for most transitions
2. **Natural physics** - Cards should feel like they have weight
3. **Purposeful motion** - Every animation should communicate state
4. **Respect user preferences** - Honor `prefers-reduced-motion`

---

## Game Stages & Screens

### 1. Connection Screen

```
┌────────────────────────────────────────────────┐
│                                                 │
│         🎴 Hungarian Tarokk 🎴                 │
│                                                 │
│         ══════════════════════                  │
│                                                 │
│    ┌──────────────────────────────┐            │
│    │  Enter Your Name             │            │
│    │  [________________]          │            │
│    └──────────────────────────────┘            │
│                                                 │
│         [Connect to Game]                       │
│                                                 │
│              ⚙️ Settings                        │
│                                                 │
└────────────────────────────────────────────────┘
```

**Features:**
- Username input with validation
- Connection status indicator
- Settings button (sound, graphics quality)
- Game rules link

**Implementation:**
```typescript
<ConnectionScreen>
  <GameTitle />
  <PlayerNameInput
    value={playerName}
    onChange={setPlayerName}
    onSubmit={handleConnect}
  />
  <ConnectButton
    disabled={!playerName || isConnecting}
    onClick={handleConnect}
  />
  <SettingsButton />
  <RulesLink />
</ConnectionScreen>
```

---

### 2. Lobby Screen

```
┌────────────────────────────────────────────────┐
│  🏠 Lobby               Your Name   [Logout]   │
├────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐  ┌─────────────┐             │
│  │ Create Room │  │ Join Room   │             │
│  └─────────────┘  └─────────────┘             │
│                                                 │
│  Active Rooms:                                  │
│  ┌──────────────────────────────────────────┐  │
│  │ Room #AB12   🟢  [Join]   3/4 players  │  │
│  │ Room #CD34   🟡  [Join]   2/4 players  │  │
│  │ Room #EF56   🟢  [Join]   3/4 players  │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
│  Or enter room code: [______]  [Go]            │
│                                                 │
└────────────────────────────────────────────────┘
```

**Features:**
- Create new room button
- List of active rooms with player counts
- Join room by code input
- Room status indicators (🟢 ready to start, 🟡 waiting for players, 🔴 in progress)
- Player count display
- Logout button

**Implementation:**
```typescript
<LobbyScreen>
  <Header>
    <UserInfo name={playerName} />
    <LogoutButton />
  </Header>

  <ActionButtons>
    <CreateRoomButton onClick={handleCreateRoom} />
    <JoinRoomButton onClick={handleJoinRoom} />
  </ActionButtons>

  <RoomList>
    {rooms.map(room => (
      <RoomCard
        key={room.id}
        room={room}
        onJoin={() => handleJoinRoom(room.id)}
      />
    ))}
  </RoomList>

  <QuickJoin>
    <Input placeholder="Room code" />
    <Button>Go</Button>
  </QuickJoin>
</LobbyScreen>
```

---

### 3. Waiting Room

```
┌────────────────────────────────────────────────┐
│  Room: #AB12          [Leave Room]  [Ready]   │
├────────────────────────────────────────────────┤
│                                                 │
│          Waiting for players...                 │
│                                                 │
│  ┌───────────┐  ┌───────────┐                  │
│  │ Position 0│  │ Position 1│                  │
│  │   Alice   │  │    Bob    │                  │
│  │  ✅ Ready │  │  ⏳ Not   │                  │
│  └───────────┘  └───────────┘                  │
│                                                 │
│  ┌───────────┐  ┌───────────┐                  │
│  │ Position 2│  │ Position 3│                  │
│  │  Charlie  │  │  (Empty)  │                  │
│  │  ✅ Ready │  │           │                  │
│  └───────────┘  └───────────┘                  │
│                                                 │
│  Share room code: AB12  [Copy]                 │
│                                                 │
│  💬 Chat: [Type message...]                    │
│                                                 │
└────────────────────────────────────────────────┘
```

**Features:**
- Show all 4 player positions
- Ready status indicators
- Leave room button
- Ready/Not Ready toggle
- Room code display with copy button
- Optional: Chat for coordination
- Game starts automatically when all 4 ready

**Implementation:**
```typescript
<WaitingRoom>
  <Header>
    <RoomCode code={roomId} />
    <LeaveButton />
    <ReadyButton
      isReady={isReady}
      onClick={toggleReady}
    />
  </Header>

  <PlayerGrid>
    {[0, 1, 2, 3].map(position => (
      <PlayerSlot
        key={position}
        player={players[position]}
        position={position}
        isYou={position === myPosition}
      />
    ))}
  </PlayerGrid>

  <ShareSection>
    <RoomCodeDisplay code={roomId} />
    <CopyButton />
  </ShareSection>

  <ChatBox messages={messages} />
</WaitingRoom>
```

---

### 4. Main Game Screen Layout

This is the core layout used for all game phases (Bidding, Discarding, Playing, etc.)

```
┌──────────────────────────────────────────────────────────────┐
│  🎴 Room #AB12    Phase: Bidding    Turn: Bob    [Menu]     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│                    ┌───────────┐                             │
│                    │   Bob     │  <- Top player              │
│                    │  9 cards  │                             │
│                    └───────────┘                             │
│                                                               │
│  ┌───────────┐              TABLE              ┌──────────┐ │
│  │  Charlie  │                                  │  Diana   │ │
│  │  9 cards  │       (Center Area)             │ 9 cards  │ │
│  └───────────┘      Current Trick               └──────────┘ │
│                     Announcements                             │
│                                                               │
│                    ┌───────────┐                             │
│                    │   Alice   │  <- You (bottom)            │
│                    │  (YOU)    │                             │
│                    └───────────┘                             │
│                                                               │
│            ┌─────────────────────────┐                       │
│            │ 🂠 🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨 │  <- Your hand       │
│            └─────────────────────────┘                       │
│                                                               │
│  ┌────────────────────────────────────────┐                 │
│  │ Action Area: [Pass] [Bid: 2] [Bid: 1] │  <- Actions      │
│  └────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

**Key Areas:**

1. **Top Bar** (fixed)
   - Room code
   - Current phase
   - Current turn indicator
   - Menu button (settings, rules, leave)

2. **Game Table** (center)
   - 4 player positions (top, left, right, bottom=you)
   - Center area for:
     - Current trick (during playing)
     - Bid history (during bidding)
     - Announcements display
     - Talon cards (when visible)

3. **Your Hand** (bottom)
   - Cards displayed in a fan/arc
   - Hover effects
   - Click/tap to select
   - Visual indicators for selected cards

4. **Action Area** (bottom bar)
   - Context-sensitive action buttons
   - Changes based on game phase
   - Disabled when not your turn

5. **Side Panel** (optional, collapsible)
   - Bid history
   - Announcements made
   - Score tracking
   - Game log

---

### 5. Dealing Phase

```
┌──────────────────────────────────────────────────┐
│         🎴 Dealing Cards... 🎴                   │
│                                                   │
│                  ┌───────┐                       │
│                  │ Deck  │  <- Animated deck     │
│                  │ 🎴 🎴 │     dealing cards     │
│                  └───────┘                       │
│                     ↓↓↓                          │
│        Cards being dealt to players...           │
│                                                   │
│  Alice: ████████░ 8/9                            │
│  Bob:   ███████░░ 7/9                            │
│  Charlie: ████░░░░ 4/9                           │
│  Diana: █████░░░░ 5/9                            │
│                                                   │
└──────────────────────────────────────────────────┘
```

**Features:**
- Animated card dealing from central deck
- Progress bars for each player
- Smooth card flip animations
- Cards dealt counter-clockwise
- 6 cards to talon first (hidden)
- Then 5 to each player, then 4 more

**Animation Sequence:**
1. Shuffle animation (2s)
2. 6 cards to talon (face down) - 0.3s each
3. 5 cards to each player - 0.2s per card
4. 4 cards to each player - 0.2s per card
5. Transition to bidding phase

---

### 6. Bidding Phase

```
┌──────────────────────────────────────────────────────────────┐
│  Phase: BIDDING    Current Turn: Bob 🔔                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│                    ┌───────────┐                             │
│                    │   Bob     │  🔔 <- Thinking indicator   │
│                    │ ⏳ Bidding │                            │
│                    └───────────┘                             │
│                                                               │
│                                                               │
│  Bid History:                    Highest Bid:                │
│  ┌─────────────────────────┐    ┌──────────────┐           │
│  │ Alice: THREE (1pt) 🏆   │    │  Bob: TWO    │           │
│  │ Bob:   TWO (2pt)        │    │  (2 points)  │           │
│  │ Charlie: PASS           │    └──────────────┘           │
│  │ Diana: PASS             │                                │
│  └─────────────────────────┘                                │
│                                                               │
│            ┌─────────────────────────┐                       │
│            │ 🂠 🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨 │  <- Your hand       │
│            └─────────────────────────┘                       │
│                                                               │
│  Your turn! Select your bid:                                 │
│  ┌──────────────────────────────────────────────┐           │
│  │ [PASS] [THREE: 1pt] [TWO: 2pt] [ONE: 3pt]  │           │
│  │              ❌ SOLO: 4pt (disabled)         │           │
│  └──────────────────────────────────────────────┘           │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Real-time bid history display
- Current highest bid highlighted
- Valid bids shown (disabled if invalid)
- Tooltip explaining each bid type
- Timer/countdown (optional)
- Visual indicator of whose turn it is
- Honour card requirement indicator

**Bid Button States:**
- ✅ **Available** - Green, clickable
- 🔒 **Locked** - Grey, tooltip explains why ("Need honour card", "Bid too low")
- ⏳ **Thinking** - Pulsing for current player

**Mobile Adaptation:**
- Swipe gestures for bid selection
- Larger touch targets
- Compact bid history (collapsible)

---

### 7. Talon Distribution Phase

```
┌──────────────────────────────────────────────────────────────┐
│  Phase: TALON DISTRIBUTION    Declarer: Bob                  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│             Talon Cards Being Distributed                     │
│                                                               │
│               ┌──┐ ┌──┐ ┌──┐                                │
│               │🎴│ │🎴│ │🎴│  <- Talon (6 cards)            │
│               └──┘ └──┘ └──┘                                │
│                  ↓   ↓   ↓                                   │
│                                                               │
│  Bob (Declarer): +2 cards  ✅                                │
│  Alice: +1 card  ⏳                                          │
│  Charlie: +2 cards  ⏳                                        │
│  Diana: +1 card  ⏳                                           │
│                                                               │
│  You received: +1 card                                        │
│            ┌─────────────────────────────┐                   │
│            │ 🂠 🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨 🂪 │ <- Now 10 cards  │
│            └─────────────────────────────┘                   │
│                                                               │
│  Waiting for all players to receive talon cards...           │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Animated card distribution from talon
- Show how many cards each player receives
- New cards in your hand highlighted briefly
- Progress indicator for distribution
- Clear indication of declarer

**Animation:**
1. Talon cards flip up (revealing they exist, not their faces)
2. Cards fly to respective players (0.3s each)
3. Player hand sizes update
4. Brief "glow" effect on new cards
5. Transition to discarding phase

---

### 8. Discarding Phase

```
┌──────────────────────────────────────────────────────────────┐
│  Phase: DISCARDING    Your Turn    Discard 1 card           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ⚠️ Cannot discard: Kings or Honours (skíz, XXI, pagát)     │
│                                                               │
│  Players Status:                                              │
│  Bob: ✅ Discarded | Alice: ⏳ Discarding (you!)             │
│  Charlie: ⏳ Waiting | Diana: ⏳ Waiting                      │
│                                                               │
│            ┌─────────────────────────────┐                   │
│            │ 🂠 🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨 🂪 │                  │
│            │     ↑ Selected              │                   │
│            └─────────────────────────────┘                   │
│                   Your hand (10 cards)                        │
│                                                               │
│  Selected: 1/1 cards  ✅                                     │
│  ┌────────────────────────────────────────┐                 │
│  │        [Confirm Discard]                │                 │
│  └────────────────────────────────────────┘                 │
│                                                               │
│  💡 Tip: Discard low-value cards you don't need             │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Clear indication of how many cards to discard
- Selected cards raised/highlighted
- Invalid cards (Kings, Honours) shown with lock icon
- Confirm button only enabled when correct number selected
- Real-time validation feedback
- Progress indicator showing who has discarded

**Interaction:**
1. Click/tap cards to select (cards raise up)
2. Selected count updates
3. Confirm button becomes available
4. Click confirm to discard
5. Cards animate to discard pile (center, face down)

**Visual Feedback:**
- Valid cards: Normal brightness
- Invalid cards: Dimmed with 🔒 overlay
- Selected cards: Raised 20px with glow
- Hover effect: Card tilts slightly

---

### 9. Partner Call Phase

```
┌──────────────────────────────────────────────────────────────┐
│  Phase: PARTNER CALL    Declarer: Bob (calling partner)     │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│        Bob is calling their partner...                        │
│                                                               │
│  ┌────────────────────────────────────────────┐             │
│  │  Select which Tarokk to call:              │             │
│  │                                             │             │
│  │  [XX] [XIX] [XVIII] [XVII] [XVI] [XV]     │             │
│  │  [XIV] [XIII] [XII] [XI] [X] [IX] [VIII]  │             │
│  │                                             │             │
│  │  💡 Typical call: XX (Tarokk 20)          │             │
│  └────────────────────────────────────────────┘             │
│                                                               │
│            ┌─────────────────────────────┐                   │
│            │ 🂠 🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨  │                  │
│            └─────────────────────────────┘                   │
│                   Your hand (9 cards)                         │
│                                                               │
│  ⚠️ The player holding the called card becomes your partner! │
│  🤐 Their identity stays secret until the card is played.    │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Only declarer can interact (others see waiting screen)
- Grid of tarokk cards to choose from
- Recommended call highlighted (typically XX)
- Explanation of partner call mechanics
- Cards you hold are disabled (can't call your own cards)

**Non-Declarer View:**
```
┌──────────────────────────────────────────────────────────────┐
│  Phase: PARTNER CALL    Bob is selecting partner...         │
│                                                               │
│              ⏳ Waiting for Bob...                           │
│                                                               │
│  Bob is deciding which Tarokk to call.                       │
│  The player holding that card will be their partner.         │
│                                                               │
│  🤔 Are you the partner? You'll find out when                │
│     the called card is played!                               │
└──────────────────────────────────────────────────────────────┘
```

---

### 10. Announcements Phase

```
┌──────────────────────────────────────────────────────────────┐
│  Phase: ANNOUNCEMENTS    Your Turn                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Announcement History:                                        │
│  ┌────────────────────────────────────────┐                 │
│  │ Bob: TRULL (announced) - 2 pts         │                 │
│  │ Alice: (passed)                        │                 │
│  │ Charlie: FOUR KINGS (silent) - 1 pt    │                 │
│  │ Diana: (your turn)                     │                 │
│  └────────────────────────────────────────┘                 │
│                                                               │
│            ┌─────────────────────────────┐                   │
│            │ 🂠 🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨  │                  │
│            └─────────────────────────────┘                   │
│                   Your hand (9 cards)                         │
│                                                               │
│  You can announce:                                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ✅ TRULL (all 3 honours)                             │    │
│  │    [Announce: 2pts] or [Silent: 1pt]                │    │
│  │                                                       │    │
│  │ ✅ DOUBLE GAME (predict 71+ points)                  │    │
│  │    [Announce: 2x multiplier]                         │    │
│  │                                                       │    │
│  │ 🔒 FOUR KINGS (need all 4 kings) - unavailable      │    │
│  │ 🔒 PAGÁT ULTIMÓ (need pagát) - unavailable          │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  [Pass]    (3 consecutive passes ends phase)                 │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- List of available announcements with point values
- Clear distinction between "announced" (full points) and "silent" (half points)
- Unavailable announcements shown as locked with explanation
- Announcement history visible
- Pass button always available
- Tooltip explaining each announcement type

**Announcement Cards:**
Each available announcement shows:
```
┌─────────────────────────────────┐
│ TRULL                          │
│ All 3 honours (skíz, XXI, I)  │
│                                │
│ [Announce: 2 pts] [Silent: 1pt]│
│                                │
│ ℹ️ You score these points at   │
│   the end if you made them    │
└─────────────────────────────────┘
```

---

### 11. Playing Phase (Trick-Taking)

```
┌──────────────────────────────────────────────────────────────┐
│  Phase: PLAYING    Trick 3/9    Your Turn                    │
│  Declarer: Bob (TWO) | Partner: ??? (called XX)             │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│                    ┌───────────┐                             │
│                    │   Bob     │                             │
│                    │  6 cards  │                             │
│                    └───────────┘                             │
│                                                               │
│  ┌──────┐                           ┌──────┐                │
│  │Charlie│      Current Trick:      │Diana │                │
│  │7 cards│     ┌──┐ ┌──┐ ┌──┐      │6 cards│               │
│  └──────┘      │🂡│ │🂤│ │? │      └──────┘                │
│                 └──┘ └──┘ └──┘                               │
│               Bob  Alice  Charlie                            │
│               Lead   +2    +0                                 │
│                                                               │
│  Announcements Active:                                        │
│  🏆 Bob: TRULL (announced)    🤫 Charlie: FOUR KINGS (silent)│
│                                                               │
│            ┌─────────────────────────────┐                   │
│            │ 🂠 🂡 🂢 🂣 🂤 🂥 🂦 🂧 🂨  │                  │
│            │         ↑ valid             │                   │
│            └─────────────────────────────┘                   │
│                   Your hand (7 cards)                         │
│                                                               │
│  💡 Must follow suit (Hearts) or play Tarokk if void        │
│  Valid cards are highlighted                                  │
└──────────────────────────────────────────────────────────────┘
```

**Features:**

1. **Trick Display (Center)**
   - Cards played so far in current trick
   - Player names under each card
   - Point value shown (if valuable card)
   - Lead card highlighted

2. **Player Information**
   - Card counts for each player
   - Current turn indicator (animated arrow/glow)
   - Declarer and partner indicators (once revealed)

3. **Your Hand**
   - Cards sorted by suit/rank
   - Valid cards highlighted/raised
   - Invalid cards dimmed (can't play)
   - Hover preview shows card enlarged

4. **Game Information Bar**
   - Current trick number (3/9)
   - Active announcements
   - Score preview

**Trick Animation Sequence:**
1. Players play cards (fly to center) - 0.5s each
2. Last card played
3. Pause 1s showing trick
4. Winner determination animation (glow on winning card)
5. Cards fly to winner's trick pile - 1s
6. Points added with "+X points" popup
7. Next trick begins

**Partner Reveal:**
When the called card (e.g., XX) is played:
```
┌────────────────────────────────┐
│   🎊 PARTNER REVEALED! 🎊     │
│                                │
│    Charlie is Bob's partner!   │
│                                │
│  Teams:                        │
│  Declarer: Bob & Charlie       │
│  Opponents: Alice & Diana      │
└────────────────────────────────┘
```

---

### 12. Trick Complete Modal

```
┌──────────────────────────────────┐
│    ✅ Trick Won by Alice!       │
├──────────────────────────────────┤
│                                  │
│  Cards in trick:                 │
│  ┌──┐ ┌──┐ ┌──┐ ┌──┐          │
│  │🂡│ │🂤│ │🂷│ │🂨│          │
│  └──┘ └──┘ └──┘ └──┘          │
│  Bob  Alice Charlie Diana       │
│                                  │
│  Points: 8                       │
│  Winner: Alice (highest tarokk) │
│                                  │
│      [Continue]                  │
└──────────────────────────────────┘
```

**Features:**
- Shows all 4 cards from trick
- Point value highlighted
- Winner explanation ("highest tarokk", "king of lead suit")
- Auto-dismiss after 3s or manual continue

---

### 13. Scoring Phase

```
┌──────────────────────────────────────────────────────────────┐
│                    🏆 GAME OVER 🏆                           │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Final Scores:                                                │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  DECLARER TEAM (Bob & Charlie)          52 pts 🏆  │    │
│  │  ─────────────────────────────────────────────────  │    │
│  │  Tricks won: 5                          42 pts     │    │
│  │  Discards:                              10 pts     │    │
│  │  Trull (announced):                     +2 pts     │    │
│  │  Four Kings (silent):                   +1 pt      │    │
│  │  ─────────────────────────────────────────────────  │    │
│  │  Game Value (TWO):                      2 pts      │    │
│  │  Multiplier (Double Game):              ×2         │    │
│  │  Final Payment:                         +8 pts     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  OPPONENT TEAM (Alice & Diana)          42 pts     │    │
│  │  ─────────────────────────────────────────────────  │    │
│  │  Tricks won: 4                          42 pts     │    │
│  │  Discards:                              0 pts      │    │
│  │  ─────────────────────────────────────────────────  │    │
│  │  Final Payment:                         -8 pts     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│              [Play Again]    [Leave Room]                    │
└──────────────────────────────────────────────────────────────┘
```

**Features:**
- Detailed score breakdown
- Team division clearly shown
- Trick-by-trick review (optional expandable)
- Announcement bonuses calculated
- Game value and multipliers shown
- Individual player payments
- Celebration animation for winners
- Play again or leave options

**Extended View (Optional):**
- Button to view all 9 tricks
- Replay any trick
- Export game log

---

## Component Library

### Core Components

#### 1. Card Component

```typescript
interface CardProps {
  suit: 'tarokk' | 'hearts' | 'diamonds' | 'spades' | 'clubs'
  rank: string
  size: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  orientation: 'portrait' | 'landscape' | 'facedown'
  selectable: boolean
  selected: boolean
  disabled: boolean
  onClick?: () => void
  onHover?: () => void
  style?: 'classic' | 'modern' | 'minimal'
}

<Card
  suit="tarokk"
  rank="XXI"
  size="md"
  selectable
  selected={isSelected}
  onClick={handleCardClick}
/>
```

**States:**
- Default
- Hover (raise + shadow)
- Selected (raised higher + glow)
- Disabled (greyed out + lock icon)
- Playing (flying to trick)
- In trick (smaller, in center)

#### 2. Player Avatar Component

```typescript
interface PlayerAvatarProps {
  name: string
  position: 0 | 1 | 2 | 3
  isYou: boolean
  isCurrentTurn: boolean
  cardCount: number
  isConnected: boolean
  isDeclarer?: boolean
  isPartner?: boolean
  isRevealed?: boolean
}

<PlayerAvatar
  name="Bob"
  position={1}
  isCurrentTurn={true}
  cardCount={7}
  isDeclarer={true}
/>
```

**Visual Elements:**
- Avatar/Icon
- Name label
- Card count badge
- Turn indicator (animated ring)
- Status badges (declarer 👑, partner 🤝)
- Connection status (🟢 connected, 🔴 disconnected)

#### 3. Hand Component

```typescript
interface HandProps {
  cards: Card[]
  selectedCards: string[]
  validCards?: string[]
  onCardClick: (cardId: string) => void
  layout: 'fan' | 'straight' | 'compact'
  maxWidth: number
}

<Hand
  cards={hand}
  selectedCards={selectedCards}
  validCards={validCardIds}
  onCardClick={handleCardSelect}
  layout="fan"
/>
```

**Layouts:**
- **Fan** - Cards arranged in arc (classic)
- **Straight** - Linear with overlap
- **Compact** - For mobile, scrollable

#### 4. Action Button Component

```typescript
interface ActionButtonProps {
  label: string
  variant: 'primary' | 'secondary' | 'danger' | 'success'
  size: 'sm' | 'md' | 'lg'
  disabled?: boolean
  loading?: boolean
  icon?: React.ReactNode
  onClick: () => void
  tooltip?: string
}

<ActionButton
  label="Confirm Discard"
  variant="primary"
  size="lg"
  disabled={selectedCards.length !== requiredCount}
  onClick={handleDiscard}
/>
```

#### 5. GameLog Component

```typescript
<GameLog>
  <LogEntry type="bid" player="Bob">
    Bob bid TWO (2 points)
  </LogEntry>
  <LogEntry type="card_played" player="Alice">
    Alice played King of Hearts
  </LogEntry>
  <LogEntry type="trick_won" player="Charlie">
    Charlie won trick 3 (8 points)
  </LogEntry>
</GameLog>
```

**Features:**
- Auto-scroll to latest
- Filter by type (bids, plays, tricks)
- Click entry to highlight related cards
- Collapsible on mobile

#### 6. Modal Component

```typescript
<Modal
  isOpen={showRules}
  onClose={() => setShowRules(false)}
  title="Game Rules"
  size="lg"
>
  <RulesContent />
</Modal>
```

**Types of Modals:**
- Rules
- Settings
- Confirmation dialogs
- Scoring breakdown
- Trick review

---

## Animations & Transitions

### Card Animations

#### 1. Deal Animation
```typescript
// Stagger cards dealing to players
const dealAnimation = {
  initial: { x: 0, y: 0, rotateY: 180 },
  animate: (i: number) => ({
    x: targetPosition.x,
    y: targetPosition.y,
    rotateY: 0,
    transition: {
      delay: i * 0.1,
      duration: 0.5,
      ease: "easeOut"
    }
  })
}
```

#### 2. Card Play Animation
```typescript
// Card flying from hand to trick
const playCardAnimation = {
  initial: { scale: 1 },
  animate: {
    x: [0, centerX],
    y: [0, centerY],
    scale: [1, 1.2, 0.8],
    rotateY: [0, 10, 0],
    transition: {
      duration: 0.6,
      ease: "easeInOut"
    }
  }
}
```

#### 3. Trick Won Animation
```typescript
// Cards flying to winner's pile
const trickWonAnimation = {
  animate: {
    x: winnerX,
    y: winnerY,
    scale: 0.3,
    opacity: 0.5,
    transition: {
      duration: 0.8,
      ease: "easeIn",
      delay: 1 // Show trick first
    }
  },
  onComplete: () => {
    // Add points popup
    showPointsEarned(trickPoints)
  }
}
```

#### 4. Card Selection
```typescript
// Raise card on select
const selectAnimation = {
  y: selected ? -20 : 0,
  boxShadow: selected
    ? "0 10px 30px rgba(0,0,0,0.5)"
    : "0 4px 8px rgba(0,0,0,0.2)",
  transition: {
    type: "spring",
    stiffness: 300,
    damping: 20
  }
}
```

### UI Transitions

#### Phase Transitions
```typescript
// Fade out old phase, fade in new
const phaseTransition = {
  exit: { opacity: 0, y: -20 },
  enter: { opacity: 1, y: 0 },
  transition: { duration: 0.3 }
}
```

#### Turn Indicator
```typescript
// Pulsing glow for current player
const turnIndicator = {
  scale: [1, 1.1, 1],
  boxShadow: [
    "0 0 0px rgba(59, 130, 246, 0)",
    "0 0 20px rgba(59, 130, 246, 0.8)",
    "0 0 0px rgba(59, 130, 246, 0)"
  ],
  transition: {
    duration: 2,
    repeat: Infinity,
    ease: "easeInOut"
  }
}
```

### Loading States

#### Skeleton Loading
```typescript
<SkeletonCard /> // Pulsing card placeholder
<SkeletonText /> // Pulsing text placeholder
<SkeletonAvatar /> // Pulsing avatar placeholder
```

#### Spinner
```typescript
<Spinner size="lg" /> // For async actions
```

---

## Responsive Design

### Breakpoints

```css
/* Mobile First */
--breakpoint-sm: 640px;   /* Mobile landscape */
--breakpoint-md: 768px;   /* Tablet */
--breakpoint-lg: 1024px;  /* Desktop */
--breakpoint-xl: 1280px;  /* Large desktop */
--breakpoint-2xl: 1536px; /* Ultra-wide */
```

### Layout Adaptations

#### Desktop (≥1024px)
```
┌────────────────────────────────────┐
│     Top Player (vertical)          │
│                                     │
│  Left    Center Table    Right     │
│ Player    (Tricks)       Player    │
│(rotated)                 (rotated) │
│                                     │
│     Your Hand (fan layout)         │
│     Action Buttons (horizontal)    │
└────────────────────────────────────┘
```

#### Tablet (768px - 1023px)
```
┌────────────────────────────────────┐
│     Top Player (compact)           │
│                                     │
│  Left   Center   Right             │
│ Player  Table   Player             │
│ (icons) (compact) (icons)          │
│                                     │
│  Your Hand (straight with scroll)  │
│  Action Buttons (stacked)          │
└────────────────────────────────────┘
```

#### Mobile (< 768px)
```
┌─────────────────────┐
│   Top (3 avatars)   │
│      in a row       │
├─────────────────────┤
│                     │
│   Center Table      │
│   (Compact view)    │
│                     │
├─────────────────────┤
│  Your Hand          │
│  (Swipe carousel)   │
├─────────────────────┤
│  Actions (Bottom)   │
│  [Pass] [Bid: 2]    │
└─────────────────────┘
```

### Touch Optimizations

**Mobile Gestures:**
- **Tap** - Select card
- **Double tap** - Play card immediately
- **Long press** - Show card details
- **Swipe left/right** - Navigate through hand
- **Swipe up** - Show game log
- **Pinch** - Zoom cards (accessibility)

**Touch Targets:**
- Minimum 44×44 px (Apple) / 48×48 px (Android)
- Spacing between interactive elements: 8px minimum

---

## Accessibility

### WCAG 2.1 AA Compliance

#### 1. Keyboard Navigation
```typescript
// All actions must be keyboard accessible
- Tab: Navigate between interactive elements
- Enter/Space: Activate buttons, select cards
- Arrow keys: Navigate through hand
- Escape: Close modals
- 1-9 keys: Quick select cards
```

#### 2. Screen Reader Support
```typescript
<Card
  role="button"
  aria-label="King of Hearts, 5 points, selectable"
  aria-pressed={isSelected}
  aria-disabled={!isValid}
  tabIndex={0}
/>

<PlayerAvatar
  role="status"
  aria-live="polite"
  aria-label="Bob, 7 cards remaining, current turn"
/>
```

#### 3. Visual Accessibility

**Color Contrast:**
- Text: Minimum 4.5:1 ratio
- Large text (18pt+): Minimum 3:1
- UI components: Minimum 3:1

**Color Blindness:**
- Don't rely solely on color
- Use patterns/icons for suits
- Red (♥️ ♦️) - solid fill
- Black (♠️ ♣️) - outline
- Tarokk - distinctive icon ⚜️

**High Contrast Mode:**
```css
@media (prefers-contrast: high) {
  .card {
    border: 3px solid currentColor;
  }
  .selected {
    outline: 5px solid yellow;
  }
}
```

#### 4. Reduced Motion
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }

  .card-animation {
    /* Skip flying animations, use fade instead */
    animation: fade 0.3s;
  }
}
```

#### 5. Focus Indicators
```css
*:focus-visible {
  outline: 3px solid var(--color-info);
  outline-offset: 2px;
}

.card:focus-visible {
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.5);
}
```

#### 6. Text Alternatives
- All icons have `aria-label`
- Images have `alt` text
- Decorative elements use `aria-hidden="true"`
- Card symbols use both icon + text

#### 7. Language Support
```html
<html lang="en"> <!-- or "hu" for Hungarian -->

<!-- Internationalization ready -->
<Text i18nKey="game.phase.bidding">Bidding</Text>
```

---

## Performance Optimizations

### 1. Code Splitting
```typescript
// Lazy load phases
const BiddingPhase = lazy(() => import('./phases/BiddingPhase'))
const PlayingPhase = lazy(() => import('./phases/PlayingPhase'))

<Suspense fallback={<PhaseLoading />}>
  {phase === 'bidding' && <BiddingPhase />}
  {phase === 'playing' && <PlayingPhase />}
</Suspense>
```

### 2. Asset Optimization
```typescript
// Use WebP with fallback
<picture>
  <source srcset="card-back.webp" type="image/webp" />
  <img src="card-back.png" alt="Card back" />
</picture>

// Lazy load card images
<img
  src={cardImage}
  loading="lazy"
  decoding="async"
/>
```

### 3. Virtual Scrolling
```typescript
// For large game logs
<VirtualList
  height={400}
  itemCount={logEntries.length}
  itemSize={50}
  renderItem={(index) => <LogEntry entry={logEntries[index]} />}
/>
```

### 4. Memoization
```typescript
// Expensive calculations
const sortedHand = useMemo(
  () => sortCards(hand),
  [hand]
)

// Expensive components
const PlayerAvatar = memo(({ player }) => {
  // ... component implementation
})
```

### 5. Debouncing/Throttling
```typescript
// Throttle hover effects
const handleCardHover = useThrottle((cardId) => {
  setHoveredCard(cardId)
}, 50)
```

---

## Network Handling

### Connection States

```typescript
enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error'
}
```

### Offline Handling

```
┌────────────────────────────────────┐
│  ⚠️ Connection Lost                │
│                                     │
│  Attempting to reconnect...        │
│  [Retry Now]                       │
│                                     │
│  Your game state is saved.         │
└────────────────────────────────────┘
```

**Features:**
- Automatic reconnection attempts (exponential backoff)
- Manual retry button
- Save game state locally
- Resume game on reconnection
- Show connection quality indicator

### Latency Optimization

```typescript
// Optimistic UI updates
function playCard(cardId: string) {
  // 1. Update UI immediately
  removeCardFromHand(cardId)
  addCardToTrick(cardId)

  // 2. Send to server
  socket.emit('play_card', { card_id: cardId })

  // 3. Rollback if server rejects
  socket.on('error', (err) => {
    addCardBackToHand(cardId)
    showError(err.message)
  })
}
```

---

## Sound Design

### Sound Categories

#### 1. UI Sounds
- Button click: Soft click
- Card hover: Subtle whoosh
- Modal open/close: Gentle chime
- Error: Negative beep
- Success: Positive chime

#### 2. Game Sounds
- **Card dealing**: Shuffle + dealing swish
- **Card play**: Card sliding on felt
- **Trick won**: Victory chime + coins
- **Phase change**: Gong or bell
- **Your turn**: Gentle notification

#### 3. Ambient Sounds (Optional)
- Background music (very subtle, can disable)
- Ambient café/pub sounds (optional theme)

### Sound Implementation
```typescript
class SoundManager {
  private sounds: Map<string, HTMLAudioElement>
  private volume: number = 0.5
  private muted: boolean = false

  play(soundId: string, volume?: number) {
    if (this.muted) return
    const sound = this.sounds.get(soundId)
    sound.volume = volume ?? this.volume
    sound.play()
  }

  // Preload critical sounds
  preload(['card_play', 'card_deal', 'your_turn'])
}
```

---

## Testing Strategy

### Unit Tests
- Card component rendering
- Hand sorting logic
- Valid card calculation
- Score calculation

### Integration Tests
- Phase transitions
- Socket.IO communication
- State management
- User actions → server updates

### E2E Tests (Playwright/Cypress)
```typescript
test('Complete game flow', async () => {
  // 1. Connect 4 players
  // 2. Deal cards
  // 3. Complete bidding
  // 4. Discard
  // 5. Call partner
  // 6. Play all tricks
  // 7. Verify scores
})
```

### Visual Regression Tests
- Screenshot comparison for each phase
- Different screen sizes
- Different themes (if multiple)

---

## Deployment

### Build Configuration

```bash
# Development
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

### Environment Variables
```bash
VITE_SERVER_URL=https://tarokk-server.example.com
VITE_ENABLE_DEV_TOOLS=false
VITE_ANALYTICS_ID=
```

### Hosting Options
1. **Vercel** (recommended for Next.js/React)
2. **Netlify**
3. **AWS Amplify**
4. **Static hosting** (any CDN)

---

## Future Enhancements

### Phase 2 Features
- [ ] Spectator mode
- [ ] Tournament system
- [ ] Replays/game history
- [ ] Player statistics
- [ ] Achievements/badges
- [ ] Custom card backs/themes
- [ ] Voice chat integration
- [ ] Mobile app (React Native)

### Phase 3 Features
- [ ] AI opponents
- [ ] Tutorial mode (interactive)
- [ ] Advanced analytics
- [ ] Season rankings
- [ ] Custom game rules
- [ ] Social features (friends, chat)

---

## Summary

This design document provides a comprehensive blueprint for building a modern, accessible, and performant Hungarian Tarokk client. The key principles are:

1. **Progressive Enhancement** - Start with web, can evolve to native
2. **Responsive First** - Works on all devices
3. **Accessible** - WCAG AA compliant
4. **Performant** - Optimized for smooth animations
5. **Maintainable** - Component-based architecture
6. **Extensible** - Easy to add features

The technology stack (React + TypeScript + Socket.IO) integrates perfectly with your existing Python server and provides a solid foundation for building a world-class card game client.

**Next Steps:**
1. Set up React project with TypeScript
2. Implement connection + lobby screens
3. Build card and player components
4. Implement game table layout
5. Add phase-specific UIs
6. Polish with animations
7. User testing and iteration
