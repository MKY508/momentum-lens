# Momentum Lens Smart Cleanup Plan

## Analysis Summary

- Files analyzed: 6
- Total unused imports: 26
- Safe to remove: 2
- Potentially useful (kept): 24

## Imports to Remove (Definitely Unused)

- **dataSourceManager** in `App.tsx`: Not used in component
- **ListItemSecondaryAction** in `APIConfiguration.tsx`: Not using secondary actions

## Imports to Keep (Potentially Useful)

- **CircularProgress** in `App.tsx`: Loading states
- **Alert** in `App.tsx`: Error/success messages
- **SpeedIcon** in `DataSourceStatus.tsx`: Performance
- **useState** in `CoreModule.tsx`: State management
- **addDays** in `CoreModule.tsx`: Date manipulation
- **Holding** in `CoreModule.tsx`: Holdings type
- **DCASchedule** in `CoreModule.tsx`: DCA schedule type
- **useEffect** in `DecisionDashboard.tsx`: Side effects
- **InfoIcon** in `DecisionDashboard.tsx`: Information display
- **Decision** in `DecisionDashboard.tsx`: Decision type
- **MarketIndicator** in `DecisionDashboard.tsx`: Market data type
- **FilterIcon** in `LogsKPI.tsx`: Filtering
- **LineChart** in `LogsKPI.tsx`: Line charts
- **Line** in `LogsKPI.tsx`: Chart lines
- **BarChart** in `LogsKPI.tsx`: Bar charts
- **Bar** in `LogsKPI.tsx`: Chart bars
- **TradeLog** in `LogsKPI.tsx`: Trade log type
- **AlertType** in `LogsKPI.tsx`: Alert type
- **PerformanceMetrics** in `LogsKPI.tsx`: Performance type
- **Stack** in `APIConfiguration.tsx`: Layout stacking
- **LinearProgress** in `APIConfiguration.tsx`: Progress bars
- **Paper** in `APIConfiguration.tsx`: Card containers
- **useQuery** in `APIConfiguration.tsx`: Data fetching
- **useMutation** in `APIConfiguration.tsx`: Data mutations

## Port Configuration Fix

Standardizing all ports:
- Frontend: 3000
- Backend API: 8000
- WebSocket: ws://localhost:8000