# Tarokk: phone-friendly screens, bots, tutorial hints, Hungarian

Date: 2026-11-12
Status: draft, awaiting approval

Throughout this document, **(decided)** marks something the project owner said
or approved, and **(builder's call)** marks a choice made while writing this
design that the owner has not explicitly confirmed.

## 1. Intent

The game works today as a desktop web app for four humans. Three things are
wrong with it for the owner:

- On a phone it is not meaningfully playable. The hand is small, the table is
  far away, and choosing a card means scrolling.
- You need four humans. There is no way to play alone or to fill a missing
  seat.
- A newcomer gets no help with the hard decisions (what to bid, what to put in
  the skart, what to announce, what to play).

The work is four pieces, built in this order. After each piece the game must
still be fully playable.

1. Phone-friendly screens for the whole app, installable as a PWA.
2. Bots that can fill seats, running on the server.
3. Tutorial hints, driven by the same rules the bots use.
4. Hungarian localisation, with English kept as the second language.

## 2. Goals, non-goals, anti-goals

**Goals**

- A full hand can be played comfortably, one-handed, on a phone in portrait,
  with no sideways scrolling and no pinch-zoom, on screens from 360x640 up.
- The same app still works well on tablet and desktop.
- One person can start a game against three bots in one tap.
- A table owner can mix humans and bots, choose who sits where, and replace a
  dropped player with a bot.
- With tutorial on, every decision point shows one recommended action and a
  one-sentence reason.
- Every user-visible text exists in Hungarian and English.

**Non-goals**

- Playing offline. The game stays online-only (decided). The PWA is for
  install and full screen.
- Strong bots, difficulty levels, or any learning/search AI. The bots follow
  simple fixed rules (decided).
- Changing game rules, scoring, or card artwork.
- Accounts, rankings, matchmaking.
- Native apps.

**Anti-goals** (these make it a failure even if it "works")

- Bots that use information a human in that seat could not have (other
  players' hands, the talon, who the partner is before it is revealed).
- Tutorial advice that contradicts what a bot would do in the same seat.
- A dropped player being thrown out or replaced automatically.
- A phone layout that is the desktop layout shrunk.

## 3. Current state (what exists)

- `server/`: Python, FastAPI + python-socketio. Game rules in
  `models/game_state.py`, `game_logic/`, `validation/rules.py`. Socket handlers
  in `networking/server.py` are keyed by socket session id and contain the
  action logic inline. Rooms in `networking/room_manager.py`; there is no
  concept of a table owner. SQLite persistence in `persistence/`. Tests with
  pytest in `server/tests/`.
- `client/`: React 18 + TypeScript + Vite + Tailwind + zustand +
  framer-motion. One screen per stage (`ConnectionScreen`, `LobbyScreen`,
  `WaitingRoomScreen`, `GameScreen` with `phases/*`, `GameOverScreen`). All
  texts are hard-coded English. No client tests. Deployed to Netlify.
- A table plays exactly one hand; "Play Again" on the game-over screen leaves
  the room. See open question in section 9.
- When a socket disconnects mid-game the player is marked disconnected and can
  rejoin by stored player id; the game simply waits at their turn.

Build on what is there: same stack, same event names where they still fit.

## 4. Piece 1: phone-friendly screens and PWA

Mockups approved by the owner are in
`.superpowers/brainstorm/15969-1794514749/content/` (`play-layout-v2.html`,
`other-phases.html`, `lobby.html`). They are wireframes for layout, not for
colours or card art; keep the existing card rendering and visual style.

### 4.1 The principle (decided)

Every in-game screen has three bands:

- **Top: the table, small.** What the others did, always in table seating:
  you at the bottom (south), then the other three at west, north, east
  according to their seat relative to yours.
- **Middle: your hand, big.**
- **Bottom: your choices,** as thumb-sized buttons (minimum 44px tall).

### 4.2 Playing a trick (decided)

Two states of one screen, switching automatically:

- **Your turn.** The hand fills most of the screen in two rows of large
  cards. Cards that may not be played are greyed. The top band is a small
  table with the cards played so far lying at N/E/S/W in front of whoever
  played them, with an empty slot at your own position. Tapping a card lifts
  it; a single button at the bottom ("Play XVII") confirms.
- **Someone else's turn.** The table is big: cards lie in front of their
  players, names and trick counts at the seats, the player to move is
  highlighted. Your hand is a small overlapping strip at the bottom; tapping
  it enlarges the hand to look at it, tapping again shrinks it.

The top bar shows the trick number, whose turn it is, and the menu button.
Keep the existing "trick won" highlight and collect animation; it must fit the
new table sizes.

### 4.3 Bidding, skart, partner call, announcements (decided)

- **Bidding:** others' bids as bubbles at their seats in the top band; hand
  big; the bids as a grid of buttons at the bottom, illegal ones disabled.
- **Skart:** cards that came from the talon carry a "new" tag. Cards that may
  not be discarded are greyed. Tapping a card moves it to a row of slots in
  the top band with a counter ("2 of 3"); tapping it there returns it. The
  bottom button is disabled until the count is right.
- **Partner call (builder's call, same pattern):** hand big, callable tarokks
  as a row of buttons, XX pre-selected.
- **Announcements:** what has been announced so far at the seats in the top
  band; hand slightly smaller; announcements as toggle chips; one confirm
  button naming the selection, and a Pass button. Kontra/rekontra options
  appear as chips only when legal.

### 4.4 Lobby, waiting room, settings, game over (decided unless marked)

- **Lobby:** one column. "Play against bots" (creates a table, fills it with
  three bots, starts immediately). "New table". The list of open tables is on
  the screen itself, not in a pop-up. A field to join by code.
- **Waiting room:** the four seats drawn around a table. Each empty seat has
  "+ Add bot". Buttons: "Fill with bots", "Share invite", and one big "I'm
  ready". Chat opens from an icon as a bottom sheet. The table owner can drag
  a player or bot onto another seat; dropping on an occupied seat swaps the
  two. Drag must work with touch. Only the owner can add/remove bots and move
  seats. Bots are always ready.
- **Share invite (builder's call):** a link `…/?room=<room id>` sent through
  the Web Share API, falling back to copy-to-clipboard. Opening the link
  joins that table after the name is entered. The room id stays as it is.
- **Settings:** reachable from every screen including mid-game. Tutorial
  hints on/off, language (Magyar/English), sounds on/off. These three are
  stored per device. Bot speed (fast/normal/slow) is shown here too but is a
  **table** setting only the owner can change (builder's call, because the
  bots run on the server).
- **Sounds (builder's call):** three short sounds generated in the browser
  (your turn, card played, trick won). No audio files. Default on.
- **Game over (builder's call):** same content as today in one column:
  result first, then per-player scores, then announcement details collapsed.

### 4.5 Larger screens (builder's call)

One set of components. Below about 900px wide the two-state behaviour of 4.2
applies. Above it there is room for both, so the table stays big and the hand
stays big at once and nothing swaps. Landscape phones use the wide layout if
tall enough, otherwise the portrait logic with the table band on the left.

### 4.6 PWA (decided: installable, online-only)

- Web app manifest, icons, `display: standalone`, portrait preferred, theme
  colours matching the table.
- Service worker that caches the app shell so it opens instantly. Use
  `vite-plugin-pwa` (builder's call).
- Safe-area insets respected (notch, home indicator). Viewport height handled
  with dynamic viewport units so the bottom buttons are never under the
  browser bar.
- With no network: a clear "No connection, reconnecting…" state, automatic
  retry, and return to the same table and seat when the network is back.

### 4.7 Dropping out and coming back (decided unless marked)

- When a player's connection drops mid-game their seat shows "lost
  connection" and the game waits at their turn. Nobody is removed.
- Their client retries by itself and, once back, is in the same seat with the
  same cards.
- Everyone sees a message when a player drops ("Anna lost connection") and
  when they are back ("Anna is online again").
- Only the table owner sees "Replace with bot" on a disconnected seat.
  Nothing is replaced automatically.
- A replaced player may still come back. They take the seat over from the bot
  at once, and the "online again" message is shown.
- If the owner drops, ownership passes to the next connected human in seat
  order (builder's call). If the owner returns they do not get it back
  automatically.

**Before the game starts and between hands (builder's call):**

- Seats are four fixed places, not a list that closes up when someone
  leaves. This is needed for seat dragging anyway.
- A human whose connection drops in the waiting room keeps their seat for 2
  minutes and is shown as "lost connection". On a phone, sharing the invite
  switches apps and can drop the connection, so the table must survive that.
  After 2 minutes the seat is freed.
- The table stays open and listed while any human holds a seat, including a
  held one. Ownership passes only once the owner's seat has been freed. A
  table with no human seat left is closed.
- Leaving on purpose ("Leave table") frees the seat at once.
- Between hands the owner may add, remove and move bots and players exactly
  as in the waiting room.

"Replace with bot" belongs to piece 2 since it needs bots; the rest of 4.7 is
piece 1.

## 5. Piece 2: bots

### 5.0 Rule corrections first

"No rule changes" (section 2) has one exception. The current engine departs
from the rules in five places that the bots depend on. These are fixed, with
tests, before any bot code. Items 1 to 4 follow the standard rules in
`server/HUNGARIAN_TAROKK_RULES.md` and were put to the owner, who answered
item 5 and raised no objection to the rest.

1. **Hold (tartom).** Only a player who bid earlier may hold a later, higher
   bid. If the others then pass, the holder is the declarer. Today the later
   bidder wins and two players can hold back and forth forever.
2. **A pass is final.** A player who has passed is not asked again in that
   auction. The auction ends when all but one have passed (or on solo, or
   when all four pass).
3. **Everyone speaks in the announcement round.** Each of the four players
   gets at least one turn; after that the round ends on three passes in a
   row. Today the fourth player can be skipped.
4. **Several announcements are one turn.** Announcing two things at once
   moves the turn on by one seat, not two.
5. **What may not go into the skart (decided):** the XX, the skíz, the
   pagát, the XXI and the kings. Today the XX can be discarded, and calling
   it then fails. The skart screen greys out the XX as well.

6. **The called tarokk is in the skart (decided).** A declarer who holds the
   XX calls a lower tarokk, for example the XIX, and another player may have
   discarded it. Then:
   - the declarer plays alone, one against three;
   - the player who discarded the called card is not the partner;
   - that player must kontra the game;
   - the call never fails with an error.

How item 6 is built (builder's call):

- The engine has kontra only on announcements today, not on the game itself.
  Add a kontra on the game that doubles the game value, used for this
  obligatory case. The server applies it automatically when the discarder's
  turn comes in the announcement round, shown to everyone as that player
  saying "kontra" on the game, which is also how the table learns the
  declarer is alone. A freely chosen kontra on the game, and rekontra on it,
  are not added.
- Invit is not implemented in this game, so the "unless the called card was
  protected by an invit" condition never applies. Invit stays out of scope.
- Bots and hints treat a declarer known to be alone as having no partner.

### 5.1 Shape (builder's call)

- Bots live on the server in a new package `server/bots/`.
- A seat is a `Player` with a new flag saying whether a bot is currently
  playing it. Replacing a dropped human flips the flag; the human returning
  flips it back. The player's identity, hand and tricks do not change.
- The decision logic is a set of pure functions: given what that seat can
  legitimately see (own hand, own discards, bids, announcements, cards played,
  revealed partner, seat positions), return an action and a reason. The reason
  is a message key plus parameters, not English text, so piece 4 can translate
  it. The same functions produce tutorial hints in piece 3.
- The action logic that today sits inside the socket handlers in
  `networking/server.py` is extracted so that a human's socket event and a
  bot's decision go through the same code path and the same validation.
- After any state change, if the seat to move is bot-controlled, the server
  waits the table's bot delay (fast 0.3s, normal 1s, slow 2s) and then plays
  the bot's action. A bot must never act out of turn or twice, including
  after a server restart with persisted rooms.
- Bots have a robot marker and Hungarian first names ("Bot Jani"). A bot
  replacing a human shows as the human's name with the robot marker.
- New owner-only events: add bot, remove bot, fill with bots, swap seats (all
  only before the game starts), replace disconnected player with bot, set bot
  speed. Room info gains owner id and per-seat bot flag; both are persisted.

### 5.2 Rules the owner gave (decided)

**Bidding**

- No honour (skíz, XXI, pagát): pass.
- Holds the XXI: always bids and keeps outbidding up to "one". Never solo.
- Holds the skíz, not the XXI: with 4 or more other tarokks, pass (the hand
  is strong already; no need for the talon or a partner). With fewer than 4
  other tarokks, bid to improve the hand.
- Holds only the pagát: opens the bidding only with at least 8 tarokks,
  otherwise pass.

**Announcements, as the caller's partner** (the bot knows it is the partner
because it holds the called card)

- At least 6 tarokks: announce four kings.
- At least 5 tarokks higher than XIII: announce double game.

**Leading a trick as a defender, when no trull has been announced**

- Assume your fellow defender holds the XXI and the other side will try to
  catch it.
- If your fellow defender plays last in this trick, lead a tarokk, so they
  can get the XXI home after seeing everything.
- Otherwise lead a suit card, not a tarokk.

**Always**

- Count the tarokks that have been played, so the bot knows whether a pagát
  ulti can be made or stopped.
- Obey the rules of the game.

### 5.3 Everything else (builder's call, kept deliberately simple)

**Bidding details**

- "Bid" means the lowest legal bid, or "hold" when that is legal.
- XXI holder stops (passes) when only solo is left.
- Skíz holder with a weak hand and pagát holder with 8 tarokks bid up to
  "two" and then pass.
- With several honours the first matching rule in the order XXI, skíz, pagát
  applies.

**Skart**

- Never kings, honours or the XX (rule, see 5.0).
- Discard suit cards first, emptying the shortest suits in which the bot has
  no king, highest-point cards first.
- Discard tarokks only when no suit card may be discarded, lowest first.

**Partner call**

- Call XX. If the bot holds XX itself, call the highest tarokk below XX that
  it does not hold.

**Announcements beyond 5.2**

- Trull: only when the bot holds all three honours and at least 7 tarokks.
- Pagát ulti: only when the bot holds the pagát and at least 9 tarokks, or 8
  tarokks of which three are XVII or higher. (Changed during the build: with
  the first rule, 7 tarokks, the simulation showed the ulti failing three
  times out of four and the trull more often than not.)
- Never volát, never XXI catch, never kontra or rekontra.
- A bot never repeats an announcement and otherwise passes, so the phase
  always ends.

**Applying the defender lead rule**

- It applies only while the XXI has not been played and the bot does not hold
  it.
- "Fellow defender" is known once the partner is revealed. Before that the
  bot does not know who it is and leads a suit card.

**Other leads**

- Declarer side with more tarokks than half of those still out: lead the
  highest tarokk that is not the XXI while the skíz is out.
- Otherwise lead the lowest card of the longest suit.

**Following in a trick** (always from the legal cards)

- Holding the skíz and an opponent's XXI is in the trick: play the skíz.
- Never play the XXI while the skíz is still out and an opponent plays after
  you, unless it is the only legal card.
- A known teammate is winning the trick: add the highest-point card that
  does not waste a high tarokk.
- Can win and the trick holds points, or the bot plays last: win with the
  lowest card that wins.
- Otherwise play the lowest-value legal card.

**Pagát and tarokk counting**

- A bot that announced pagát ulti keeps the pagát for the last trick and
  leads tarokks to draw the others out.
- A bot defending against an announced pagát ulti keeps one tarokk above the
  pagát for the last trick whenever the rules let it.
- A bot holding the pagát without an ulti announcement plays it into a trick
  a known teammate is winning, or keeps it for last when its count shows all
  other tarokks are gone.

## 6. Piece 3: tutorial hints

- A switch in settings, off by default (builder's call), stored per device.
- Hints in every phase: bidding, skart, partner call, announcements, card
  play (decided).
- The hint is exactly what a bot would do in that seat, with its reason
  (decided). Shown as the yellow box from the mockups between the top band
  and the hand; the recommended button or card(s) also get a soft highlight
  (builder's call).
- The player is never forced to follow the hint.
- The server computes the hint for the human whose turn it is and sends it
  with the existing "your turn" message as key + parameters; the client shows
  it only when the switch is on (builder's call).
- Each reason reads as one plain sentence a beginner understands, naming the
  cards it is about ("You hold the XXI, so bid and try to win the talon").

## 7. Piece 4: Hungarian localisation

- Every user-visible text moves out of the components into message files,
  Hungarian and English. This includes bot hint reasons, bid and announcement
  names, toasts, the drop/return messages and error messages.
- Hungarian is the default when the device language is Hungarian, otherwise
  English; the choice in settings overrides and is remembered (builder's
  call).
- Use `i18next` with `react-i18next` (builder's call).
- Use the real table vocabulary: licit, passz, három / kettő / egy / szóló,
  tartom, skart, hívás, bemondások, tuletroá, négy király, duplajáték, volát,
  pagátultimó, XXI-fogás, kontra, rekontra, skíz, pagát, ütés.
- Server errors reach the client as free English text today. The server keeps
  its error codes; the client shows a translated message per code and falls
  back to the server text (builder's call).
- The owner is a native speaker and reviews the Hungarian texts before this
  piece is called done.

## 8. Checking that it works

- **Bots (pytest):** unit tests for each rule in 5.2 and 5.3 from fixed
  hands; a test that a bot's view contains nothing hidden from that seat; a
  simulation that plays several hundred complete four-bot hands and asserts
  no illegal action, no stall, and a valid score every time.
- **Server:** tests for owner-only actions, seat swapping, replace with bot,
  a human taking the seat back, owner hand-over, and that existing tests
  still pass after the handler extraction.
- **Client:** add Vitest for pure logic only (seat-to-screen mapping, message
  files having the same keys in both languages). Layout is checked by hand at
  360x640, 390x844, a tablet size and desktop, in both languages, for every
  screen, and on a real phone installed as a PWA.
- **Hints:** a test that for the same seat and state the hint equals the
  bot's action.

## 9. Next hand at the same table (part of piece 1)

A table plays one hand today and "Play Again" leaves the room. That changes:

- After a hand, the table stays together with the same seats and continues
  into the next hand (decided, "very important").
- The dealer rotates one seat each hand, in the direction of play (decided).
- The player who is dealt first by the dealer (the seat after the dealer)
  starts the bidding and also leads the first trick. It is **not** the
  winner of the bidding who leads (decided). The code already does this in
  `GameState.start_playing`; it must stay true once the dealer rotates, and
  gets a test.
- Running totals per player are kept across hands, shown on the game-over
  screen under the result of the hand, and persisted (decided: running
  totals; presentation is builder's call).
- The game-over screen has "Next hand" and "Leave table". The next hand is
  dealt once every connected human has tapped "Next hand"; bots are always
  ready (builder's call).
- When all four pass and the hand is thrown in, the same dealer deals again,
  as today (builder's call).
- A human who leaves between hands leaves an empty seat the owner can fill
  with a bot or that another human can join; their running total stays with
  the seat (builder's call).

## 10. Left to the builder

- Component structure, breakpoints in detail, animation timings.
- How the handler extraction in `networking/server.py` is organised.
- Exact wording of hint reasons in English (Hungarian is reviewed by the
  owner).
- Icon artwork for the PWA.
