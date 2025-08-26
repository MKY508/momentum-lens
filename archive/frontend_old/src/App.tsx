import React, { useState, useEffect } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import {
  Box,
  CssBaseline,
  ThemeProvider,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Badge,
  Avatar,
  useMediaQuery,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  AccountBalance as CoreIcon,
  Satellite as SatelliteIcon,
  Assessment as LogsIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Api as ApiIcon,
} from '@mui/icons-material';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { lightTheme, darkTheme } from './styles/theme';
import webSocketService from './services/websocket';
import DecisionDashboard from './components/Dashboard/DecisionDashboard';
import CoreModule from './components/Core/CoreModule';
import SatelliteModule from './components/Satellite/SatelliteModule';
import LogsKPI from './components/Logs/LogsKPI';
import ParameterSettings from './components/Settings/ParameterSettings';
import APITest from './pages/APITest';
import DataSourceStatus from './components/Common/DataSourceStatus';
import { dataSourceManager } from './services/dataSourceManager';

const DRAWER_WIDTH = 240;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60000, // 1 minute
      gcTime: 300000, // 5 minutes
      retry: 3,
      refetchOnWindowFocus: false,
    },
  },
});

interface NavigationItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const navigationItems: NavigationItem[] = [
  { path: '/dashboard', label: '决策台', icon: <DashboardIcon /> },
  { path: '/core', label: 'Core模块', icon: <CoreIcon /> },
  { path: '/satellite', label: 'Satellite模块', icon: <SatelliteIcon /> },
  { path: '/logs', label: '日志/KPI', icon: <LogsIcon /> },
  { path: '/settings', label: '参数设置', icon: <SettingsIcon /> },
  { path: '/api-test', label: 'API测试', icon: <ApiIcon /> },
];

// Data Source Context
export const DataSourceContext = React.createContext<{
  activeSource: string;
  setActiveSource: (source: string) => void;
  connectionStatus: Map<string, boolean>;
}>({
  activeSource: 'akshare',
  setActiveSource: () => {},
  connectionStatus: new Map()
});

interface AppContentProps {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
}

const AppContent: React.FC<AppContentProps> = ({ isDarkMode, toggleDarkMode }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifications, setNotifications] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const isMobile = useMediaQuery('(max-width:600px)');

  useEffect(() => {
    // Initial loading
    const initializeApp = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // Connect to WebSocket
        await webSocketService.connect();
        
        // Simulate API health check
        const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/health`);
        if (!response.ok) {
          throw new Error('Backend API is not responding');
        }
        
        setIsLoading(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to initialize application');
        setIsLoading(false);
      }
    };
    
    initializeApp();

    // Subscribe to alerts
    const unsubscribeAlert = webSocketService.on('alert', (alertData: any) => {
      setNotifications((prev) => prev + 1);
      // Show alert using Alert component
      setError(`New alert: ${alertData.message}`);
      setTimeout(() => setError(null), 5000); // Auto-dismiss after 5 seconds
    });

    return () => {
      unsubscribeAlert();
      webSocketService.disconnect();
    };
  }, []);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      setMobileOpen(false);
    }
  };

  const drawer = (
    <Box>
      <Toolbar>
        <Box display="flex" alignItems="center" gap={1}>
          <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
            ML
          </Avatar>
          <Typography variant="h6" fontWeight={600}>
            Momentum Lens
          </Typography>
        </Box>
      </Toolbar>
      <Divider />
      <List>
        {navigationItems.map((item) => (
          <ListItem key={item.path} disablePadding>
            <ListItemButton
              selected={location.pathname === item.path}
              onClick={() => handleNavigation(item.path)}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { sm: `${DRAWER_WIDTH}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {navigationItems.find(item => item.path === location.pathname)?.label || 'Momentum Lens'}
          </Typography>

          <Box display="flex" alignItems="center" gap={2}>
            <DataSourceStatus compact={false} />
            
            <IconButton color="inherit" onClick={toggleDarkMode}>
              {isDarkMode ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
            
            <IconButton color="inherit">
              <Badge badgeContent={notifications} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Drawer */}
      <Box
        component="nav"
        sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
        >
          {drawer}
        </Drawer>

        {/* Desktop drawer */}
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          mt: 8,
        }}
      >
        {/* Loading Indicator */}
        {isLoading && (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
            <CircularProgress size={60} />
          </Box>
        )}
        
        {/* Error Alert */}
        {error && !isLoading && (
          <Alert 
            severity="error" 
            onClose={() => setError(null)}
            sx={{ mb: 2 }}
          >
            {error}
          </Alert>
        )}
        
        {/* Main Routes - Only show when not loading */}
        {!isLoading && (
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DecisionDashboard />} />
          <Route path="/core" element={<CoreModule />} />
          <Route path="/satellite" element={<SatelliteModule />} />
          <Route path="/logs" element={<LogsKPI />} />
          <Route path="/settings" element={<ParameterSettings />} />
          <Route path="/api-test" element={<APITest />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
        )}
      </Box>
    </Box>
  );
};

const App: React.FC = () => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme === 'dark';
  });

  const toggleDarkMode = () => {
    setIsDarkMode((prev) => {
      const newMode = !prev;
      localStorage.setItem('theme', newMode ? 'dark' : 'light');
      return newMode;
    });
  };

  const theme = isDarkMode ? darkTheme : lightTheme;

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <AppContent isDarkMode={isDarkMode} toggleDarkMode={toggleDarkMode} />
        </Router>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: isDarkMode ? '#333' : '#fff',
              color: isDarkMode ? '#fff' : '#333',
            },
          }}
        />
        {/* ReactQueryDevtools removed for compatibility */}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;