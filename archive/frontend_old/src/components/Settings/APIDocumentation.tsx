import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
  Link,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Tabs,
  Tab,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Code as CodeIcon,
  Language as LanguageIcon,
  Speed as SpeedIcon,
  Lock as LockIcon,
  LockOpen as LockOpenIcon,
} from '@mui/icons-material';
// Import syntax highlighter (install with: npm install react-syntax-highlighter @types/react-syntax-highlighter)
// import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
// import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Temporary replacement for syntax highlighting
const SyntaxHighlighter = ({ children, language, style, customStyle }: any) => (
  <pre style={{ ...customStyle, overflow: 'auto', padding: '1rem', borderRadius: '4px', backgroundColor: '#1e1e1e', color: '#d4d4d4' }}>
    <code>{children}</code>
  </pre>
);
const vscDarkPlus = {};

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
      id={`doc-tabpanel-${index}`}
      aria-labelledby={`doc-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const APIDocumentation: React.FC = () => {
  const [expanded, setExpanded] = useState<string | false>('akshare');
  const [tabValue, setTabValue] = useState(0);

  const handleChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpanded(isExpanded ? panel : false);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const apiDocs = [
    {
      id: 'akshare',
      name: 'AKShare',
      icon: <LockOpenIcon color="success" />,
      type: 'Free',
      description: 'Comprehensive Chinese market data without registration',
      features: [
        'Real-time and historical data',
        'Stocks, ETFs, indices, futures',
        'Financial reports and indicators',
        'No API key required',
        'No rate limits'
      ],
      setup: `# Installation
pip install akshare

# Usage Example
import akshare as ak

# Get ETF real-time data
etf_spot_df = ak.fund_etf_spot_em()

# Get historical data
etf_hist_df = ak.fund_etf_hist_sina(symbol="sh510300")`,
      pros: [
        'Completely free',
        'No registration required',
        'Comprehensive data coverage',
        'Well-documented API'
      ],
      cons: [
        'Data may have slight delays',
        'Dependent on third-party sources'
      ]
    },
    {
      id: 'sina',
      name: 'Sina Finance (新浪财经)',
      icon: <LockOpenIcon color="success" />,
      type: 'Free',
      description: 'Real-time quotes for Chinese stocks and ETFs',
      features: [
        'Real-time market quotes',
        'Level 1 market data',
        'Historical daily data',
        'No registration needed'
      ],
      setup: `# Direct API Usage
GET https://hq.sinajs.cn/list=sh510300,sz159949

# Response Format
var hq_str_sh510300="沪深300ETF,3.721,3.721,3.708,3.724,3.703,..."`,
      pros: [
        'Real-time data',
        'Free access',
        'Simple HTTP API'
      ],
      cons: [
        'Rate limited (1000/min)',
        'Limited to basic market data',
        'Chinese documentation only'
      ]
    },
    {
      id: 'eastmoney',
      name: 'East Money (东方财富)',
      icon: <LockOpenIcon color="success" />,
      type: 'Free',
      description: 'ETF data with IOPV values and premium/discount',
      features: [
        'ETF IOPV real-time data',
        'Premium/discount calculations',
        'Market depth data',
        'Fund flow analysis'
      ],
      setup: `# API Endpoint
GET http://push2.eastmoney.com/api/qt/stock/get?secid=1.510300

# Parameters
secid: Market.Code (0=SZ, 1=SH)
fields: Data fields to return`,
      pros: [
        'IOPV data available',
        'Comprehensive ETF metrics',
        'Free to use'
      ],
      cons: [
        'Rate limited (500/min)',
        'May require parsing',
        'Unofficial API'
      ]
    },
    {
      id: 'tushare',
      name: 'Tushare',
      icon: <LockIcon color="warning" />,
      type: 'Free tier available',
      description: 'Professional financial data interface',
      features: [
        'Comprehensive market data',
        'Financial statements',
        'Alternative data',
        'Free tier: 120 calls/min'
      ],
      setup: `# Registration
1. Visit https://tushare.pro/register
2. Register with email
3. Get your API token

# Installation & Usage
pip install tushare

import tushare as ts
ts.set_token('your_token_here')
pro = ts.pro_api()

# Get ETF data
df = pro.fund_basic(market='E')`,
      pros: [
        'Professional-grade data',
        'Well-structured API',
        'Good documentation',
        'Active community'
      ],
      cons: [
        'Registration required',
        'Limited free tier',
        'Some data requires points'
      ]
    },
    {
      id: 'yahoo',
      name: 'Yahoo Finance',
      icon: <LanguageIcon color="primary" />,
      type: 'Free',
      description: 'Global market data backup',
      features: [
        'Global market coverage',
        'Historical data',
        'Corporate actions',
        'Options data'
      ],
      setup: `# Using yfinance
pip install yfinance

import yfinance as yf

# Get ETF data
etf = yf.Ticker("510300.SS")
hist = etf.history(period="1mo")`,
      pros: [
        'Global coverage',
        'Free to use',
        'Well-maintained library'
      ],
      cons: [
        'May be blocked in some regions',
        'Rate limits apply',
        'Limited Chinese market data'
      ]
    }
  ];

  const comparisonData = [
    { feature: 'Registration Required', akshare: '❌', sina: '❌', eastmoney: '❌', tushare: '✅', yahoo: '❌' },
    { feature: 'API Key Required', akshare: '❌', sina: '❌', eastmoney: '❌', tushare: '✅', yahoo: '❌' },
    { feature: 'Rate Limit', akshare: 'None', sina: '1000/min', eastmoney: '500/min', tushare: '120/min', yahoo: '2000/hr' },
    { feature: 'Real-time Data', akshare: '✅', sina: '✅', eastmoney: '✅', tushare: '✅', yahoo: '⚠️' },
    { feature: 'Historical Data', akshare: '✅', sina: '✅', eastmoney: '✅', tushare: '✅', yahoo: '✅' },
    { feature: 'IOPV Data', akshare: '⚠️', sina: '❌', eastmoney: '✅', tushare: '✅', yahoo: '❌' },
    { feature: 'Chinese Market', akshare: '✅', sina: '✅', eastmoney: '✅', tushare: '✅', yahoo: '⚠️' },
    { feature: 'Cost', akshare: 'Free', sina: 'Free', eastmoney: 'Free', tushare: 'Freemium', yahoo: 'Free' },
  ];

  return (
    <Box>
      <Typography variant="h5" fontWeight={600} gutterBottom>
        API Documentation & Guide
      </Typography>

      <Alert severity="success" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Quick Start:</strong> Momentum Lens works out-of-the-box with AKShare - no configuration required! 
          The system will automatically use free data sources to fetch market data.
        </Typography>
      </Alert>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
        <Tab label="Data Sources" />
        <Tab label="Comparison" />
        <Tab label="Examples" />
        <Tab label="Troubleshooting" />
      </Tabs>

      <TabPanel value={tabValue} index={0}>
        {/* Data Sources Tab */}
        <Grid container spacing={3}>
          {apiDocs.map((api) => (
            <Grid item xs={12} key={api.id}>
              <Accordion expanded={expanded === api.id} onChange={handleChange(api.id)}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" alignItems="center" gap={2} width="100%">
                    {api.icon}
                    <Typography variant="h6">{api.name}</Typography>
                    <Chip label={api.type} size="small" color={api.type === 'Free' ? 'success' : 'warning'} />
                    <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto', mr: 2 }}>
                      {api.description}
                    </Typography>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                        Features
                      </Typography>
                      <List dense>
                        {api.features.map((feature, index) => (
                          <ListItem key={index}>
                            <ListItemIcon>
                              <CheckCircleIcon fontSize="small" color="success" />
                            </ListItemIcon>
                            <ListItemText primary={feature} />
                          </ListItem>
                        ))}
                      </List>

                      <Grid container spacing={2} sx={{ mt: 2 }}>
                        <Grid item xs={6}>
                          <Typography variant="subtitle2" color="success.main" gutterBottom>
                            Advantages
                          </Typography>
                          <List dense>
                            {api.pros.map((pro, index) => (
                              <ListItem key={index}>
                                <ListItemText 
                                  primary={pro} 
                                  primaryTypographyProps={{ variant: 'body2' }}
                                />
                              </ListItem>
                            ))}
                          </List>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="subtitle2" color="warning.main" gutterBottom>
                            Limitations
                          </Typography>
                          <List dense>
                            {api.cons.map((con, index) => (
                              <ListItem key={index}>
                                <ListItemText 
                                  primary={con}
                                  primaryTypographyProps={{ variant: 'body2' }}
                                />
                              </ListItem>
                            ))}
                          </List>
                        </Grid>
                      </Grid>
                    </Grid>

                    <Grid item xs={12} md={6}>
                      <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                        Setup & Usage
                      </Typography>
                      <Paper elevation={0} sx={{ bgcolor: 'grey.900', p: 2, borderRadius: 1 }}>
                        <SyntaxHighlighter 
                          language="python" 
                          style={vscDarkPlus}
                          customStyle={{ margin: 0, fontSize: '0.875rem' }}
                        >
                          {api.setup}
                        </SyntaxHighlighter>
                      </Paper>
                    </Grid>
                  </Grid>
                </AccordionDetails>
              </Accordion>
            </Grid>
          ))}
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {/* Comparison Tab */}
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Data Source Comparison
            </Typography>
            
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Feature</TableCell>
                    <TableCell align="center">AKShare</TableCell>
                    <TableCell align="center">Sina</TableCell>
                    <TableCell align="center">East Money</TableCell>
                    <TableCell align="center">Tushare</TableCell>
                    <TableCell align="center">Yahoo</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {comparisonData.map((row) => (
                    <TableRow key={row.feature}>
                      <TableCell component="th" scope="row">
                        {row.feature}
                      </TableCell>
                      <TableCell align="center">{row.akshare}</TableCell>
                      <TableCell align="center">{row.sina}</TableCell>
                      <TableCell align="center">{row.eastmoney}</TableCell>
                      <TableCell align="center">{row.tushare}</TableCell>
                      <TableCell align="center">{row.yahoo}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Alert severity="info" sx={{ mt: 3 }}>
              <Typography variant="body2">
                <strong>Recommendation:</strong> For most users, AKShare provides the best balance of features and ease of use. 
                It's completely free, requires no registration, and has no rate limits.
              </Typography>
            </Alert>
          </CardContent>
        </Card>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        {/* Examples Tab */}
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Example: Fetching ETF Data
                </Typography>
                
                <Typography variant="body2" color="text.secondary" paragraph>
                  Here's how to fetch ETF data using different sources:
                </Typography>

                <Paper elevation={0} sx={{ bgcolor: 'grey.900', p: 2, borderRadius: 1 }}>
                  <SyntaxHighlighter 
                    language="javascript" 
                    style={vscDarkPlus}
                    customStyle={{ margin: 0, fontSize: '0.875rem' }}
                  >
                    {`// Using the Data Source Manager
import { dataSourceManager } from './services/dataSourceManager';

// Fetch single ETF data
const data = await dataSourceManager.fetchData('510300');
console.log('Price:', data.price);
console.log('Change:', data.changePercent, '%');

// Fetch multiple ETFs
const symbols = ['510300', '159949', '516160'];
const batchData = await dataSourceManager.fetchBatch(symbols);

batchData.forEach((data, symbol) => {
  console.log(\`\${symbol}: \${data.price} (\${data.changePercent}%)\`);
});

// With fallback handling
try {
  const data = await dataSourceManager.fetchData('510300');
  // Process data
} catch (error) {
  console.error('All data sources failed:', error);
}`}
                  </SyntaxHighlighter>
                </Paper>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Example: Testing Connections
                </Typography>
                
                <Paper elevation={0} sx={{ bgcolor: 'grey.900', p: 2, borderRadius: 1 }}>
                  <SyntaxHighlighter 
                    language="javascript" 
                    style={vscDarkPlus}
                    customStyle={{ margin: 0, fontSize: '0.875rem' }}
                  >
                    {`// Test all configured sources
const sources = dataSourceManager.getAllSources();

for (const source of sources) {
  const isConnected = await dataSourceManager.testConnection(source.id);
  console.log(\`\${source.name}: \${isConnected ? 'Connected' : 'Failed'}\`);
}

// Switch to best available source
const sources = dataSourceManager.getAllSources()
  .sort((a, b) => a.priority - b.priority);

for (const source of sources) {
  if (await dataSourceManager.testConnection(source.id)) {
    dataSourceManager.setActiveSource(source.id);
    console.log(\`Using \${source.name}\`);
    break;
  }
}`}
                  </SyntaxHighlighter>
                </Paper>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={3}>
        {/* Troubleshooting Tab */}
        <Grid container spacing={3}>
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Common Issues & Solutions
                </Typography>

                <List>
                  <ListItem>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Connection Failed"
                      secondary="Check internet connection, verify API keys (if required), ensure you haven't exceeded rate limits"
                    />
                  </ListItem>

                  <ListItem>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Data Not Updating"
                      secondary="Clear cache, check if markets are open, verify data source is active"
                    />
                  </ListItem>

                  <ListItem>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Rate Limit Exceeded"
                      secondary="Switch to a different data source, enable caching, reduce request frequency"
                    />
                  </ListItem>

                  <ListItem>
                    <ListItemIcon>
                      <InfoIcon color="info" />
                    </ListItemIcon>
                    <ListItemText
                      primary="Tushare Registration"
                      secondary="Visit tushare.pro, register with email, get free API token (120 calls/min)"
                    />
                  </ListItem>
                </List>

                <Alert severity="info" sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    <strong>Pro Tip:</strong> Enable automatic fallback in settings to ensure continuous data availability 
                    even if your primary source fails.
                  </Typography>
                </Alert>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Debug Information
                </Typography>

                <Paper elevation={0} sx={{ bgcolor: 'grey.900', p: 2, borderRadius: 1 }}>
                  <SyntaxHighlighter 
                    language="javascript" 
                    style={vscDarkPlus}
                    customStyle={{ margin: 0, fontSize: '0.875rem' }}
                  >
                    {`// Get system statistics
const stats = dataSourceManager.getStatistics();
console.log('Active connections:', stats.activeConnections);
console.log('Failed connections:', stats.failedConnections);
console.log('Cache hit rate:', stats.cacheHitRate);

// Check configuration
const config = dataSourceManager.getConfiguration();
console.log('Active source:', config.activeSourceId);
console.log('Fallback enabled:', config.enableFallback);
console.log('Cache duration:', config.cacheDuration);

// View connection status
const status = dataSourceManager.getConnectionStatus();
status.forEach((isConnected, sourceId) => {
  console.log(\`\${sourceId}: \${isConnected ? 'OK' : 'FAIL'}\`);
});`}
                  </SyntaxHighlighter>
                </Paper>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </TabPanel>
    </Box>
  );
};

export default APIDocumentation;