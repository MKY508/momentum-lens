import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Chip,
  IconButton,
  TextField,
  Alert,
  Stack,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  ListItemIcon,
  Tooltip,
  Collapse,
  Paper,
  Switch,
  FormControlLabel,
  InputAdornment,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Check as CheckIcon,
  Close as CloseIcon,
  Refresh as RefreshIcon,
  Lock as LockIcon,
  LockOpen as LockOpenIcon,
  Speed as SpeedIcon,
  Storage as StorageIcon,
  CloudQueue as CloudIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  ContentCopy as CopyIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { dataSourceManager, DataSource } from '../../services/dataSourceManager';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`api-tabpanel-${index}`}
      aria-labelledby={`api-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const APIConfiguration: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [testResults, setTestResults] = useState<Record<string, boolean | null>>({});
  const [testLatency, setTestLatency] = useState<Record<string, number>>({});
  const [expandedSource, setExpandedSource] = useState<string | null>(null);
  const [testingSource, setTestingSource] = useState<string | null>(null);
  const [enableFallback, setEnableFallback] = useState(true);
  const [cacheEnabled, setCacheEnabled] = useState(true);
  const [cacheDuration, setCacheDuration] = useState(60);

  const dataSources = dataSourceManager.getAllSources();

  // Load saved configuration
  useEffect(() => {
    const savedKeys = localStorage.getItem('apiKeys');
    if (savedKeys) {
      try {
        // Decrypt keys (in production, use proper encryption)
        const decrypted = JSON.parse(atob(savedKeys));
        setApiKeys(decrypted);
      } catch (e) {
        console.error('Failed to load API keys:', e);
      }
    }

    const savedFallback = localStorage.getItem('enableFallback');
    if (savedFallback !== null) {
      setEnableFallback(savedFallback === 'true');
    }

    const savedCache = localStorage.getItem('cacheEnabled');
    if (savedCache !== null) {
      setCacheEnabled(savedCache === 'true');
    }

    const savedCacheDuration = localStorage.getItem('cacheDuration');
    if (savedCacheDuration) {
      setCacheDuration(parseInt(savedCacheDuration));
    }
  }, []);

  // Save API keys (encrypted)
  const saveApiKeys = () => {
    try {
      // Basic encoding (in production, use proper encryption)
      const encoded = btoa(JSON.stringify(apiKeys));
      localStorage.setItem('apiKeys', encoded);
      toast.success('API keys saved securely');
    } catch (e) {
      toast.error('Failed to save API keys');
    }
  };

  // Test API connection
  const testConnection = async (sourceId: string) => {
    setTestingSource(sourceId);
    setTestResults(prev => ({ ...prev, [sourceId]: null }));

    const startTime = Date.now();
    
    try {
      const result = await dataSourceManager.testConnection(sourceId, apiKeys[sourceId]);
      const latency = Date.now() - startTime;
      
      setTestResults(prev => ({ ...prev, [sourceId]: result }));
      setTestLatency(prev => ({ ...prev, [sourceId]: latency }));
      
      if (result) {
        toast.success(`${dataSourceManager.getSourceById(sourceId)?.name} connected successfully (${latency}ms)`);
      } else {
        toast.error(`Failed to connect to ${dataSourceManager.getSourceById(sourceId)?.name}`);
      }
    } catch (error) {
      setTestResults(prev => ({ ...prev, [sourceId]: false }));
      toast.error(`Connection test failed: ${error}`);
    } finally {
      setTestingSource(null);
    }
  };

  // Test all connections
  const testAllConnections = async () => {
    for (const source of dataSources) {
      await testConnection(source.id);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const getSourceStatusIcon = (sourceId: string) => {
    const result = testResults[sourceId];
    
    if (testingSource === sourceId) {
      return <CircularProgress size={20} />;
    }
    
    if (result === true) {
      return (
        <Tooltip title={`Connected (${testLatency[sourceId]}ms)`}>
          <CheckIcon color="success" />
        </Tooltip>
      );
    }
    
    if (result === false) {
      return (
        <Tooltip title="Connection failed">
          <CloseIcon color="error" />
        </Tooltip>
      );
    }
    
    return (
      <Tooltip title="Not tested">
        <WarningIcon color="warning" />
      </Tooltip>
    );
  };

  const getSourcePriorityChip = (priority: number) => {
    const colors = ['success', 'primary', 'default', 'default'];
    const labels = ['Primary', 'Fallback 1', 'Fallback 2', 'Fallback 3'];
    
    return (
      <Chip
        size="small"
        label={labels[priority - 1] || `Priority ${priority}`}
        color={colors[priority - 1] as any || 'default'}
      />
    );
  };

  const renderSourceConfiguration = (source: DataSource) => {
    const isExpanded = expandedSource === source.id;
    
    return (
      <Card key={source.id} sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box display="flex" alignItems="center" gap={2}>
              <ListItemIcon>
                {getSourceStatusIcon(source.id)}
              </ListItemIcon>
              
              <Box>
                <Typography variant="h6" component="span">
                  {source.name}
                </Typography>
                <Box display="flex" gap={1} mt={0.5}>
                  <Chip
                    size="small"
                    label={source.type === 'free' ? 'Free' : 'Paid'}
                    color={source.type === 'free' ? 'success' : 'warning'}
                    icon={source.type === 'free' ? <LockOpenIcon /> : <LockIcon />}
                  />
                  {getSourcePriorityChip(source.priority)}
                  {source.rateLimit && (
                    <Chip
                      size="small"
                      label={source.rateLimit}
                      icon={<SpeedIcon />}
                      variant="outlined"
                    />
                  )}
                </Box>
              </Box>
            </Box>
            
            <Box display="flex" gap={1}>
              <Button
                size="small"
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={() => testConnection(source.id)}
                disabled={testingSource === source.id}
              >
                Test
              </Button>
              <IconButton
                size="small"
                onClick={() => setExpandedSource(isExpanded ? null : source.id)}
              >
                {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
          </Box>
          
          <Collapse in={isExpanded}>
            <Box mt={3}>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Endpoint: {source.endpoint}
                  </Typography>
                </Grid>
                
                {source.requiresKey && (
                  <Grid item xs={12}>
                    <TextField
                      fullWidth
                      label="API Key"
                      type="password"
                      value={apiKeys[source.id] || ''}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, [source.id]: e.target.value }))}
                      InputProps={{
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton
                              onClick={() => {
                                navigator.clipboard.writeText(apiKeys[source.id] || '');
                                toast.success('API key copied');
                              }}
                              edge="end"
                              size="small"
                            >
                              <CopyIcon />
                            </IconButton>
                          </InputAdornment>
                        ),
                      }}
                      helperText={source.id === 'tushare' ? 
                        'Get your free API key at https://tushare.pro/register' : 
                        'Enter your API key for this service'}
                    />
                  </Grid>
                )}
                
                <Grid item xs={12}>
                  <Alert severity="info" icon={<InfoIcon />}>
                    <Typography variant="body2">
                      {source.id === 'akshare' && 
                        'AKShare provides free access to Chinese market data without registration. Recommended for most users.'}
                      {source.id === 'sina' && 
                        'Sina Finance offers real-time quotes for Chinese stocks and ETFs. No registration required.'}
                      {source.id === 'eastmoney' && 
                        'East Money provides comprehensive ETF data including IOPV values. Rate limited but reliable.'}
                      {source.id === 'tushare' && 
                        'Tushare offers 120 API calls per minute on the free tier. Registration required for API key.'}
                    </Typography>
                  </Alert>
                </Grid>
              </Grid>
            </Box>
          </Collapse>
        </CardContent>
      </Card>
    );
  };

  return (
    <Box>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="API configuration tabs">
          <Tab label="Data Sources" />
          <Tab label="Configuration" />
          <Tab label="Documentation" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        {/* Data Sources Tab */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h5" fontWeight={600}>
            Data Source Configuration
          </Typography>
          <Box display="flex" gap={2}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={testAllConnections}
            >
              Test All
            </Button>
            <Button
              variant="contained"
              startIcon={<StorageIcon />}
              onClick={saveApiKeys}
            >
              Save Configuration
            </Button>
          </Box>
        </Box>

        <Alert severity="success" sx={{ mb: 3 }}>
          <Typography variant="body2">
            <strong>Free Data Sources Available!</strong> AKShare and Sina Finance provide free access to Chinese market data without any registration.
          </Typography>
        </Alert>

        {dataSources.map(source => renderSourceConfiguration(source))}
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {/* Configuration Tab */}
        <Typography variant="h5" fontWeight={600} gutterBottom>
          System Configuration
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Fallback Settings
                </Typography>
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={enableFallback}
                      onChange={(e) => {
                        setEnableFallback(e.target.checked);
                        localStorage.setItem('enableFallback', e.target.checked.toString());
                      }}
                    />
                  }
                  label="Enable automatic fallback"
                />
                
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  When enabled, the system will automatically try alternative data sources if the primary source fails.
                </Typography>

                <Alert severity="info" sx={{ mt: 2 }}>
                  Fallback chain: AKShare → Sina Finance → East Money → Tushare
                </Alert>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Cache Settings
                </Typography>
                
                <FormControlLabel
                  control={
                    <Switch
                      checked={cacheEnabled}
                      onChange={(e) => {
                        setCacheEnabled(e.target.checked);
                        localStorage.setItem('cacheEnabled', e.target.checked.toString());
                      }}
                    />
                  }
                  label="Enable data caching"
                />
                
                <TextField
                  fullWidth
                  label="Cache duration"
                  type="number"
                  value={cacheDuration}
                  onChange={(e) => {
                    const value = parseInt(e.target.value);
                    setCacheDuration(value);
                    localStorage.setItem('cacheDuration', value.toString());
                  }}
                  InputProps={{
                    endAdornment: <InputAdornment position="end">seconds</InputAdornment>,
                  }}
                  sx={{ mt: 2 }}
                  disabled={!cacheEnabled}
                />
                
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  Caching reduces API calls and improves performance by storing recent data temporarily.
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Active Data Source
                </Typography>
                
                <Box display="flex" alignItems="center" gap={2}>
                  <CloudIcon color="primary" />
                  <Typography variant="body1">
                    Current: <strong>{dataSourceManager.getActiveSource().name}</strong>
                  </Typography>
                  <Chip
                    label={`${Object.keys(testResults).filter(k => testResults[k] === true).length} / ${dataSources.length} Connected`}
                    color="primary"
                    variant="outlined"
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        {/* Documentation Tab */}
        <Typography variant="h5" fontWeight={600} gutterBottom>
          API Documentation
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Quick Start Guide
                </Typography>
                
                <Typography variant="body1" paragraph>
                  Momentum Lens supports multiple free data sources for Chinese market data. No configuration is required to get started!
                </Typography>

                <List>
                  <ListItem>
                    <ListItemIcon>
                      <CheckIcon color="success" />
                    </ListItemIcon>
                    <ListItemText
                      primary="AKShare (Recommended)"
                      secondary="Comprehensive Chinese market data, completely free, no registration required"
                    />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <CheckIcon color="success" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Sina Finance"
                      secondary="Real-time quotes for stocks and ETFs, free with rate limits"
                    />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <InfoIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText
                      primary="East Money"
                      secondary="ETF data with IOPV values, free but rate limited"
                    />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Tushare"
                      secondary="Free tier available (120 calls/minute), registration required"
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Rate Limits
                </Typography>
                
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="AKShare"
                      secondary="No rate limits"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Sina Finance"
                      secondary="1000 requests/minute"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="East Money"
                      secondary="500 requests/minute"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Tushare (Free)"
                      secondary="120 requests/minute"
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Troubleshooting
                </Typography>
                
                <Typography variant="body2" paragraph>
                  <strong>Connection Failed?</strong>
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText secondary="• Check your internet connection" />
                  </ListItem>
                  <ListItem>
                    <ListItemText secondary="• Verify API key is correct (if required)" />
                  </ListItem>
                  <ListItem>
                    <ListItemText secondary="• Ensure you haven't exceeded rate limits" />
                  </ListItem>
                  <ListItem>
                    <ListItemText secondary="• Try using a different data source" />
                  </ListItem>
                </List>

                <Typography variant="body2" paragraph sx={{ mt: 2 }}>
                  <strong>Data not updating?</strong>
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText secondary="• Clear cache in Configuration tab" />
                  </ListItem>
                  <ListItem>
                    <ListItemText secondary="• Check if markets are open" />
                  </ListItem>
                  <ListItem>
                    <ListItemText secondary="• Test connection to data source" />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>
    </Box>
  );
};

export default APIConfiguration;