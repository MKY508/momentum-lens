# Momentum Lens Frontend

A modern React-based frontend for the Momentum Lens ETF Trading System.

## Features

- **Decision Dashboard**: Real-time ETF selection and trading decisions with environment indicators
- **Core Module**: Portfolio holdings management with rebalancing alerts and HS300 tracking
- **Satellite Module**: Momentum rankings with correlation analysis and monthly rotation
- **Logs & KPI**: Trade execution logs and performance metrics visualization
- **Settings**: Customizable trading parameters and ETF pool management

## Technology Stack

- React 18 with TypeScript
- Material-UI (MUI) for UI components
- TradingView Lightweight Charts for financial visualizations
- React Query for data fetching and caching
- Socket.io for real-time updates
- React Router for navigation

## Prerequisites

- Node.js 16+ and npm/yarn
- Backend API running on http://localhost:8000

## Installation

1. Install dependencies:
```bash
npm install
```

2. Create environment file:
```bash
cp .env.example .env
```

3. Configure environment variables in `.env`:
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000
```

## Development

Start the development server:
```bash
npm start
```

The application will be available at http://localhost:3000

## Building for Production

Create an optimized production build:
```bash
npm run build
```

The build artifacts will be stored in the `build/` directory.

## Project Structure

```
frontend/
├── public/              # Static files
├── src/
│   ├── components/      # React components
│   │   ├── Dashboard/   # Decision dashboard
│   │   ├── Core/        # Core module
│   │   ├── Satellite/   # Satellite module
│   │   ├── Logs/        # Logs and KPI
│   │   └── Settings/    # Parameter settings
│   ├── services/        # API and WebSocket services
│   ├── hooks/           # Custom React hooks
│   ├── utils/           # Utility functions
│   ├── types/           # TypeScript type definitions
│   ├── styles/          # Theme and styling
│   ├── App.tsx          # Main application component
│   └── index.tsx        # Application entry point
├── package.json         # Dependencies and scripts
└── tsconfig.json        # TypeScript configuration
```

## Key Features

### Real-time Updates
- WebSocket connection for live price updates
- Auto-refresh for market indicators
- Push notifications for alerts

### Data Visualization
- TradingView charts for price analysis
- Correlation heatmaps for ETF relationships
- Performance metrics dashboards

### User Experience
- Responsive design for mobile and desktop
- Dark/light theme support
- Export functionality (CSV/PDF)
- Keyboard shortcuts for common actions

## Available Scripts

- `npm start` - Start development server
- `npm build` - Build for production
- `npm test` - Run tests
- `npm run lint` - Lint code
- `npm run format` - Format code with Prettier

## API Integration

The frontend communicates with the backend through:
- RESTful API endpoints for data fetching
- WebSocket for real-time updates
- File downloads for export functionality

## Deployment

For production deployment:

1. Build the application:
```bash
npm run build
```

2. Serve the build folder with a static server:
```bash
npm install -g serve
serve -s build
```

Or deploy to cloud platforms like Vercel, Netlify, or AWS S3.

## License

Proprietary - All rights reserved