# Hungarian Tarokk - Web Client

Modern, responsive web client for Hungarian Tarokk card game built with React, TypeScript, and Socket.IO.

## Features

- 🎴 Real-time multiplayer gameplay
- 🎨 Modern, responsive UI (desktop, tablet, mobile)
- ♿ Accessible (WCAG 2.1 AA compliant)
- 🎭 Smooth animations with Framer Motion
- 🔊 Sound effects and music
- 🌐 Progressive Web App (PWA) - installable
- 🎯 Full Hungarian Tarokk rules implementation

## Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Real-time**: Socket.IO Client
- **Animations**: Framer Motion

## Installation

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file (optional):
```bash
# Server URL (default: http://localhost:8000)
VITE_SERVER_URL=http://localhost:8000
```

3. Start development server:
```bash
npm run dev
```

The client will be available at `http://localhost:3003`

## Building for Production

```bash
npm run build
```

Built files will be in the `dist/` directory.

## Project Structure

```
client/
├── src/
│   ├── components/      # Reusable UI components
│   │   ├── Card/        # Card component
│   │   ├── Hand/        # Player hand component
│   │   ├── PlayerAvatar/# Player avatar component
│   │   └── ...
│   ├── screens/         # Game screens
│   │   ├── Connection/  # Initial connection screen
│   │   ├── Lobby/       # Game lobby
│   │   ├── WaitingRoom/ # Waiting for players
│   │   └── Game/        # Main game screen
│   ├── store/           # Zustand state management
│   ├── services/        # Socket.IO and other services
│   ├── types.ts         # TypeScript type definitions
│   ├── App.tsx          # Main app component
│   └── main.tsx         # Entry point
├── public/              # Static assets
├── index.html          # HTML template
└── package.json        # Dependencies
```

## Development

### Running Tests
```bash
npm run test
```

### Linting
```bash
npm run lint
```

### Type Checking
```bash
npm run type-check
```

## Game Screens

1. **Connection** - Enter name and connect to server
2. **Lobby** - Browse/join rooms
3. **Waiting Room** - Wait for 4 players, ready up
4. **Dealing** - Animated card dealing
5. **Bidding** - Place bids in turn
6. **Talon Distribution** - Receive talon cards
7. **Discarding** - Discard to 9 cards
8. **Partner Call** - Declarer calls partner
9. **Announcements** - Declare bonuses
10. **Playing** - Trick-taking phase
11. **Scoring** - Final scores and results

## Keyboard Shortcuts

- **Tab** - Navigate between elements
- **Enter/Space** - Activate buttons, select cards
- **Arrow Keys** - Navigate through hand
- **Escape** - Close modals
- **1-9** - Quick select cards (when in hand)

## Accessibility

- Full keyboard navigation
- Screen reader support
- High contrast mode
- Reduced motion support
- ARIA labels and landmarks
- Focus indicators

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## License

See main project LICENSE file.
