# Mobile UI, Bots, Tutorial Hints, Hungarian: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the tarokk web app comfortably playable on a phone (installable PWA), let bots fill seats, give tutorial hints from the bots' rules, and ship Hungarian + English texts.

**Architecture:** The Python server stays the single source of game truth. Socket handlers become thin wrappers around shared action functions so humans and bots go through the same path. Bots are pure decision functions over a per-seat view; the same functions produce tutorial hints sent with `your_turn`. The React client is rebuilt around three bands (small table / big hand / thumb buttons) with every text behind `t()`.

**Tech Stack:** Python 3.12, FastAPI, python-socketio, pydantic, pytest (server). React 18, TypeScript, Vite, Tailwind, zustand, framer-motion, i18next + react-i18next, vite-plugin-pwa, Vitest (client).

**Spec:** `docs/superpowers/specs/2026-11-12-mobile-bots-tutorial-design.md` (read it; section numbers below refer to it). Approved mockups: `.superpowers/brainstorm/15969-1794514749/content/{play-layout-v2,other-phases,lobby}.html`.

## Global Constraints

- Online-only. No offline play.
- Bots and hints use only what that seat may see (own hand, own discards, bids, announcements, played cards, revealed partner, seats).
- A hint must equal the bot's action for the same seat and state.
- No dropped player is removed or replaced automatically mid-game.
- Phone portrait from 360x640: no sideways scroll, tap targets at least 44px.
- Not discardable: kings, skíz, XXI, pagát, XX.
- First bidder and first trick leader are always the seat after the dealer; the dealer rotates by one seat per hand.
- Every user-visible client string goes through `t()`; `en.json` and `hu.json` have identical key sets.
- Server code imports as `models.…`, `networking.…` (not `server.models.…`); new tests do the same.
- Run server tests with `cd server; .venv/bin/python -m pytest -q`. Run client checks with `cd client; npx tsc --noEmit; npx vitest run; npm run build`.
- In this shell `git` is a broken wrapper: use `command git`. Do not chain `cd X && …`; use `cd X; …`.
- Commit after every task on branch `feature/mobile-bots-tutorial`.

## Review Focus

1. A bot or the turn engine stalling: a state where the seat to move never acts (bot task lost after restart, replaced seat, announcement loop). Expect: every hand finishes. Pinned by Task 9 simulation and Task 8 restart test.
2. A player reconnecting with a new socket while a bot holds their seat, or twice from two tabs. Expect: one live controller per seat, no duplicate action. Pinned in Task 8.
3. Seat changes while positions are cached: swap or leave in the waiting room or between hands, then start. Expect: `players[i].position == i` at deal time and totals follow the player. Pinned in Tasks 2 and 3.
4. Declarer alone (called card in skart) through scoring. Expect: no crash with `partner_position is None`, game value doubled by the obligatory kontra. Pinned in Task 1.
5. Long names, 12 cards in hand, and Hungarian text on a 360px screen. Expect: no overflow or clipped buttons. Checked by hand in Tasks 5 to 7 and 12.

---

## Part A: server foundations for piece 1

### Task 1: Rule corrections (spec 5.0)

**Files:** Modify `server/models/game_state.py`, `server/models/card.py`, `server/models/player.py`, `server/game_logic/bidding.py`, `server/validation/rules.py`, `server/game_logic/final_scoring.py`, `server/networking/server.py`, `server/persistence/persistence_manager.py`. Test: `server/tests/test_rule_corrections.py`.

**Produces:**
- `GameState.passed_positions() -> set[int]`; `place_bid` skips passed seats when advancing `current_turn`; `is_bidding_complete()` true on solo, on all four passed, or when exactly one seat has not passed and at least one non-pass bid exists.
- Hold: legal only for a seat whose own last non-pass bid is lower than the current highest and was made before it. `get_highest_bid()` returns the latest bid among those with the highest value (so a holder wins).
- `GameState.announcement_speakers: list[int]`; `is_announcement_phase_complete()` requires all four seats to have had a turn and the last three turns to be passes. `make_announcements(position, list[Announcement])` advances the turn once.
- `Card.can_be_discarded()` false for kings, honours and XX; `validate_discard` matches.
- `GameState.declarer_alone: bool`, `GameState.called_card_discarded_by: Optional[int]`, `GameState.game_contra: bool`. `call_partner` no longer raises when the card is in a discard pile: it sets `partner_position=None`, `declarer_alone=True`, `called_card_discarded_by=<pos>`.
- `GameState.apply_obligatory_contra_if_due() -> bool`: when the seat to move in ANNOUNCEMENTS is `called_card_discarded_by` and `game_contra` is false, sets it and returns True. Server broadcasts `contra_made` with `announcement_type: "game"`.
- Scoring handles `partner_position is None` and doubles the game value when `game_contra`.
- New fields persisted and restored.

- [x] Tests (each a function in the test file): `test_holder_becomes_declarer` (A three, B two, A hold, others pass → declarer A, talon 2); `test_hold_not_legal_for_latest_bidder`; `test_passed_player_not_asked_again`; `test_auction_ends_when_one_left`; `test_all_pass_no_declarer`; `test_fourth_seat_gets_announcement_turn`; `test_two_announcements_advance_turn_once`; `test_xx_cannot_be_discarded`; `test_called_card_in_skart_declarer_alone`; `test_obligatory_contra_applied_once_and_doubles_game`; `test_scoring_without_partner`.
- [x] Run, see them fail; implement; run full suite green; commit.

### Task 2: Fixed seats, table owner, waiting-room grace

**Files:** Modify `server/networking/room_manager.py`, `server/networking/server.py`, `server/models/player.py`, persistence. Test: `server/tests/test_room_seats.py`.

**Produces:**
- `Player.is_bot: bool = False`, `Player.bot_controlled: bool = False`, `Player.total_score: int = 0`, `Player.ready_next: bool = False`.
- `Room.owner_id: Optional[str]`, `Room.bot_speed: str = "normal"` (`fast` 0.3s, `normal` 1.0s, `slow` 2.0s), `Room.free_seats() -> list[int]`, `Room.add_player` takes the lowest free seat, `Room.swap_seats(a: int, b: int)` (WAITING or GAME_END only; swaps or moves), `Room.vacate(player_id)`, `Room.pass_ownership()` (next connected non-bot human in seat order), `Room.sorted_players()` used at deal time so `players[i].position == i`.
- `get_room_info()` adds `owner_id`, `bot_speed`, `hand_number`, and per player `is_bot`, `bot_controlled`, `total_score`.
- Leaving in WAITING no longer renumbers seats. Disconnect in WAITING/GAME_END holds the seat for `WAITING_GRACE_SECONDS = 120`, then vacates; a table with no human seat (held seats count) is deleted. Explicit `leave_room` vacates at once.
- Socket events `swap_seats {from_position, to_position}` and `set_bot_speed {speed}`: owner only, else error code `NOT_OWNER`.
- `player_connection` broadcast `{player_position, player_name, connected: bool}` on every drop and return, in any phase.

- [x] Tests: `test_join_takes_lowest_free_seat`, `test_leave_keeps_other_positions`, `test_swap_occupied_seats`, `test_move_to_empty_seat`, `test_swap_rejected_mid_game`, `test_owner_is_creator`, `test_ownership_passes_to_next_human`, `test_sorted_players_at_deal`, `test_grace_expiry_vacates` (call the expiry function directly), `test_room_deleted_when_no_humans`.
- [x] Implement, full suite green, commit.

### Task 3: Next hand, rotating dealer, running totals (spec 9)

**Files:** Modify `server/models/game_state.py`, `server/networking/server.py`, persistence. Test: `server/tests/test_next_hand.py`.

**Produces:**
- `GameState.hand_number: int = 1`; `GameState.reset_for_next_hand()` clears per-hand state, sets `dealer_position = (dealer_position + 1) % 4`, increments `hand_number`.
- `handle_game_over` adds each `player_scores` entry to `Player.total_score`; `game_over` payload gains `total_scores: list[int]` and `hand_number`. Totals also in `game_state.to_dict` per player.
- Socket event `next_hand {}`: sets `ready_next`; when every connected non-bot human is ready, deals the next hand. Bots count as ready. Broadcast `room_state` after each change.

- [x] Tests: `test_dealer_rotates`, `test_first_bidder_and_first_leader_follow_dealer` (for dealers 0..3: `current_turn` at bidding start and `trick_leader` at play start equal `(dealer+1)%4`, with a declarer at another seat), `test_totals_accumulate`, `test_next_hand_waits_for_all_humans`, `test_all_pass_keeps_dealer`.
- [x] Implement, suite green, commit.

## Part B: client piece 1

### Task 4: Client foundations

**Files:** Create `client/src/i18n/{index.ts,en.json,hu.json}`, `client/src/store/settingsStore.ts`, `client/src/utils/seats.ts`, `client/src/utils/seats.test.ts`, `client/src/i18n/keys.test.ts`, `client/src/hooks/useIsWide.ts`, `client/src/utils/sound.ts`, `client/vitest.config.ts`. Modify `client/package.json`, `client/src/types.ts`, `client/src/services/socketManager.ts`, `client/src/store/gameStore.ts`, `client/src/main.tsx`.

**Produces:**
- `screenSeat(absolute: number, me: number): 'S' | 'W' | 'N' | 'E'` (relative 0 S, 1 W, 2 N, 3 E, same as today's left/top/right).
- `useSettings` zustand store persisted under `tarokk-settings` in localStorage: `tutorial: boolean` (default false), `language: 'hu' | 'en' | null`, `sound: boolean` (default true).
- i18next initialised with `en` and `hu`; language = setting, else `hu` if `navigator.language` starts with `hu`, else `en`. `hu.json` starts as a copy of `en.json` (real Hungarian in Task 12).
- `playSound(kind: 'turn' | 'card' | 'trick')` using WebAudio, no-op when the setting is off.
- `useIsWide(): boolean` for `min-width: 900px`.
- Types extended for Task 1 to 3 server fields; `socketManager` gains `swapSeats`, `setBotSpeed`, `nextHand`, handles `player_connection` (toast "X lost connection" / "X is online again"), reconnection attempts unlimited, and all toasts go through `t()`.
- Invite link: on load, `?room=<id>` is remembered and joined after the name is entered.

- [x] Vitest: `seats.test.ts` (all 16 combinations), `keys.test.ts` (same key set in both files).
- [x] `npx tsc --noEmit`, `npx vitest run`, commit.

### Task 5: Shared game components

**Files:** Create under `client/src/components/`: `TopBar.tsx`, `MiniTable.tsx`, `BigTable.tsx`, `HandGrid.tsx`, `HandStrip.tsx`, `ActionBar.tsx`, `GameLayout.tsx`, `SettingsSheet.tsx`, `ChatSheet.tsx`, `ConnectionBanner.tsx`, `HintBox.tsx`. Modify `Card.tsx`, `index.css`, `index.html`, `tailwind.config.js`.

**Produces:**
- `GameLayout({ top, hand, actions, hint? })`: full dynamic-viewport-height column with safe-area padding; on wide screens top and hand both large.
- `MiniTable` / `BigTable({ seats: Record<'S'|'W'|'N'|'E', ReactNode>, highlight? })`: compass placement; children decide content (card, bid bubble, announcement bubble, name).
- `HandGrid({ cards, selected, disabled, tagged, onTap, size })`: rows of up to 5 (9 cards) or 6 (12 cards), sorted with existing `cardSorting`, disabled greyed, `tagged` shows "new".
- `HandStrip({ cards, onTap })` overlapping small cards.
- `ActionBar` children are buttons at least 44px tall.
- `HintBox({ hint })` renders only when the tutorial setting is on (used from Task 11; renders nothing without a hint).
- `SettingsSheet`: tutorial, language, sound; bot speed shown only to the owner.
- `ConnectionBanner`: "No connection, reconnecting…" whenever the socket is not connected.

- [x] `npx tsc --noEmit`, build, commit.

### Task 6: Game phase screens

**Files:** Rewrite `client/src/screens/GameScreen.tsx`, `phases/PlayingPhase.tsx`, `phases/BiddingPhase.tsx`, `phases/DiscardingPhase.tsx`, `phases/PartnerCallPhase.tsx`, `phases/AnnouncementsPhase.tsx`, `GameOverScreen.tsx`.

Behaviour per spec 4.2, 4.3, 4.4 and the mockups. Specific decisions:
- Playing, my turn: `MiniTable` + `HandGrid` + one button "Play <card>". Otherwise `BigTable` + `HandStrip`; tapping the strip toggles an enlarged read-only `HandGrid` overlay. Wide screens always show `BigTable` + `HandGrid`.
- Trick-won highlight stays; the collect animation flies toward the winner's compass seat.
- Skart: selected cards render in slots in the top band with "n of m"; XX, kings, honours disabled.
- Announcements: chips for `valid_announcements`, kontra/rekontra chips when legal, confirm button names the selection, Pass button. A `contra_made` with type `game` shows as "kontra" at that seat.
- Seats with `is_connected === false` show "lost connection".
- Game over: result, per-player hand score and running total, collapsed announcement details, buttons "Next hand" (shows who is still waited for) and "Leave table".

- [x] `npx tsc --noEmit`, build, play one full hand in four browser tabs against the local server at 390x844 and at desktop width, commit.

### Task 7: Connection, lobby, waiting room, PWA

**Files:** Rewrite `ConnectionScreen.tsx`, `LobbyScreen.tsx`, `WaitingRoomScreen.tsx`. Create `client/public/` icons and `client/scripts/make-icons.py`. Modify `vite.config.ts`, `index.html`, `package.json`.

- Lobby: "Play against bots" button is added in Task 10; here "New table", inline open-table list (auto-refresh 5s), join by code.
- Waiting room: four seats on a table via `BigTable`; owner drags seats (pointer events, works with touch; tap-seat-then-tap-seat as fallback); "Share invite" (`navigator.share`, else clipboard); "I'm ready"; chat sheet.
- PWA: `vite-plugin-pwa` with `registerType: 'autoUpdate'`, manifest name "Tarokk", `display: 'standalone'`, `orientation: 'portrait'`, theme/background `#0f3d2e`, icons 192/512/maskable, precache app shell only; `viewport-fit=cover`.

- [x] Build; confirm `dist/manifest.webmanifest` and `dist/sw.js` exist; hand check at 360x640; commit.

## Part C: bots (piece 2)

### Task 8: Shared actions, bot seats, bot runner

**Files:** Create `server/networking/actions.py`, `server/bots/__init__.py`, `server/bots/runner.py`, `server/bots/names.py`. Modify `server/networking/server.py`, `room_manager.py`, `pyproject.toml` (add `bots`, `persistence` to packages). Test: `server/tests/test_actions_and_bot_seats.py`.

**Produces:**
- `actions.py`: `async def act_bid(room, player, bid_type: BidType)`, `act_discard(room, player, card_ids: list[str])`, `act_call_partner(room, player, rank: str)`, `act_announce(room, player, types: list[AnnouncementType])`, `act_pass_announcement(room, player)`, `act_contra(room, player, type: str)`, `act_recontra(room, player, type: str)`, `act_play_card(room, player, card_id: str)`. Each validates turn and phase, mutates state, broadcasts, then calls `after_action(room)`, which sends `your_turn`, applies the obligatory kontra, saves, and calls `runner.schedule(room)`. Socket handlers only resolve room/player and call these. Broadcast helpers move here and take an injected emitter so tests can run without sockets.
- `Room.turn_seq: int` incremented by every action. `runner.schedule(room)`: if the seat to move is bot-controlled, start one asyncio task that sleeps the table delay, then acts only if `turn_seq` is unchanged. Called also after rooms load from persistence, on replace-with-bot, and on next hand.
- Owner-only socket events: `add_bot {position}`, `remove_bot {position}`, `fill_bots {}` (WAITING or GAME_END), `replace_with_bot {position}` (mid-game, seat must be disconnected). Bots: `is_bot=True`, `bot_controlled=True`, `is_ready=True`, `is_connected=True`, names from `names.py` (`Bot Jani`, `Bot Kati`, `Bot Pista`, `Bot Juli`, `Bot Feri`, `Bot Marcsi`), unique per table.
- A human rejoining a seat with `bot_controlled=True` sets it False (and `turn_seq += 1` so a pending bot task dies); `player_connection` is broadcast. A second socket for the same player replaces the first.
- Until Task 9 the runner's decision function is a stub that plays the first legal option.

- [x] Tests: `test_existing_flow_through_actions` (a scripted hand via `act_*`), `test_add_remove_fill_bots_owner_only`, `test_replace_requires_disconnected`, `test_human_takes_seat_back_cancels_bot`, `test_stale_bot_task_does_not_act` (turn_seq changed), `test_second_socket_replaces_first`.
- [x] Suite green, commit.

### Task 9: Bot strategy (spec 5.2, 5.3)

**Files:** Create `server/bots/view.py`, `server/bots/strategy.py`, `server/bots/counting.py`. Test: `server/tests/test_bot_strategy.py`, `server/tests/test_bot_simulation.py`.

**Produces:**
- `SeatView` (dataclass): `position, hand, own_discards, dealer_position, bid_history, valid_bids, declarer_position, called_rank, partner_position (only if revealed), i_am_partner, declarer_alone (only if the kontra was shown), announcements, announcement_history, valid_announcements, current_trick, trick_history, legal_cards, discard_count, phase`. `build_view(game_state, position) -> SeatView`.
- `Decision` (dataclass): `action: str` (`bid|discard|call_partner|announce|pass_announcement|play_card`), `payload: dict`, `reason_key: str`, `reason_params: dict`.
- `decide(view: SeatView) -> Decision`, dispatching to `decide_bid`, `decide_discard`, `decide_call`, `decide_announcement`, `decide_card`.
- `counting.tarokks_out(view) -> list[int]` (tarokk values not in own hand, own discards, or played), `skiz_out(view)`, `xxi_out(view)`.
- Reason keys are namespaced `hint.<phase>.<rule>` (for example `hint.bid.xxi_always`, `hint.bid.skiz_strong_pass`, `hint.lead.partner_last_tarokk`), each with params naming the cards.
- Runner uses `decide`.

- [ ] Strategy tests, one per rule in 5.2 and 5.3 from fixed hands, including: XXI bids up to one then passes at solo; skíz with 4 other tarokks passes, with 3 bids; pagát with 8 tarokks opens, with 7 passes, and does not overbid; partner with 6 tarokks announces four kings; partner with 5 tarokks above XIII announces double game; bot never repeats an announcement; defender leads tarokk when the revealed fellow defender plays last, a suit otherwise and before reveal; rule off when trull announced or XXI played or held; skíz catches an opponent's XXI; XXI not played while skíz is out and an opponent follows; discard never contains a protected card and has the right count; call is XX, or the highest tarokk below XX not held.
- [ ] `test_view_hides_hidden_info`: the view has no other hands, no talon, no unrevealed partner.
- [ ] `test_bot_simulation`: 300 seeded four-bot hands through `act_*` with zero delay; assert no exception, every hand reaches GAME_END within 200 actions, card points total 94 per hand, per-hand player scores sum to zero.
- [ ] Suite green, commit.

### Task 10: Bot UI

**Files:** Modify `WaitingRoomScreen.tsx`, `LobbyScreen.tsx`, `GameScreen.tsx`, `BigTable.tsx`/seat rendering, `socketManager.ts`, `types.ts`, `en.json`, `hu.json`.

- Waiting room and between hands: "+ Add bot" on empty seats, remove on bot seats, "Fill with bots" (owner only).
- Lobby: "Play against bots" = create table, fill bots, ready.
- In game: robot marker on bot-controlled seats; owner sees "Replace with bot" on a disconnected seat.

- [x] tsc, build, play one hand against three bots locally on a phone-sized viewport, commit.

## Part D: tutorial hints (piece 3)

### Task 11: Hints end to end

**Files:** Modify `server/networking/actions.py` (in `send_your_turn`), `client/src/types.ts`, `HintBox.tsx`, phase screens, `en.json`, `hu.json`. Test: `server/tests/test_hints.py`.

- `your_turn` gains `hint: {action, payload, reason_key, reason_params}` computed with `decide(build_view(...))` for non-bot seats.
- Client: `HintBox` shows `t(reason_key, reason_params)` between the top band and the hand when the tutorial setting is on; the recommended button, chip or card(s) get a soft highlight. Card params are translated to display names on the client.

- [ ] `test_hint_equals_bot_decision` across a seeded hand in every phase; `test_hint_absent_for_bots`.
- [ ] English text for every `hint.*` key the strategy can emit (`test_all_reason_keys_have_text` reads `client/src/i18n/en.json`).
- [ ] Suite green, tsc, build, commit.

## Part E: Hungarian (piece 4)

### Task 12: Hungarian texts

**Files:** `client/src/i18n/hu.json`, `client/src/i18n/errors.ts`, `socketManager.ts`.

- Translate every key using the vocabulary in spec section 7. Server error codes map to translated messages, falling back to the server text.
- Grep the client for leftover hard-coded user-visible English.

- [ ] `keys.test.ts` green; hand check of every screen in Hungarian at 360x640; commit.

### Task 13: Wrap-up

- [ ] Full server suite, `npx tsc --noEmit`, `npx vitest run`, `npm run build`.
- [ ] Update `README.md` (bots, tutorial, PWA, languages, next hand) and `client/IMPLEMENTATION_STATUS.md`.
- [ ] Write `docs/superpowers/plans/2026-11-12-status.md`: what is done, what was checked how, what the owner must check (Hungarian wording, real-phone install, server deploy).
- [ ] Commit and push.
