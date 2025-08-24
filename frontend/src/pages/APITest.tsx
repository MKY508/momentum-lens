import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  LinearProgress,
  Alert,
  Tabs,
  Tab,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Timer as TimerIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { dataSourceManager } from '../services/dataSourceManager';
import toast from 'react-hot-toast';

interface TestResult {
  sourceId: string;
  sourceName: string;
  symbol: string;
  success: boolean;
  latency: number;
  data?: any;
  error?: string;
  timestamp: Date;
}

interface BenchmarkResult {
  sourceId: string;
  sourceName: string;
  avgLatency: number;
  minLatency: number;
  maxLatency: number;
  successRate: number;
  totalRequests: number;
  failedRequests: number;
}

const APITest: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [testSymbol, setTestSymbol] = useState('510300');
  const [isTestingAll, setIsTestingAll] = useState(false);
  const [isTestingSingle, setIsTestingSingle] = useState<string | null>(null);
  const [isBenchmarking, setIsBenchmarking] = useState(false);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [benchmarkResults, setBenchmarkResults] = useState<BenchmarkResult[]>([]);
  const [benchmarkProgress, setBenchmarkProgress] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  // Test single source
  const testSingleSource = async (sourceId: string) => {
    setIsTestingSingle(sourceId);
    
    const source = dataSourceManager.getSourceById(sourceId);
    if (!source) {
      toast.error('Source not found');
      setIsTestingSingle(null);
      return;
    }

    const startTime = Date.now();
    
    try {
      // First test connection
      const connected = await dataSourceManager.testConnection(sourceId);
      if (!connected) {
        const result: TestResult = {
          sourceId,
          sourceName: source.name,
          symbol: testSymbol,
          success: false,
          latency: Date.now() - startTime,
          error: 'Connection failed',
          timestamp: new Date()
        };
        
        setTestResults(prev => [result, ...prev].slice(0, 50));
        toast.error(`${source.name} connection failed`);
        return;
      }

      // Then fetch data
      const tempManager = Object.create(dataSourceManager);
      tempManager.setActiveSource(sourceId);
      const data = await tempManager.fetchData(testSymbol, false);
      
      const latency = Date.now() - startTime;
      
      const result: TestResult = {
        sourceId,
        sourceName: source.name,
        symbol: testSymbol,
        success: !!data,
        latency,
        data,
        error: data ? undefined : 'No data returned',
        timestamp: new Date()
      };
      
      setTestResults(prev => [result, ...prev].slice(0, 50));
      
      if (data) {
        toast.success(`${source.name} test successful (${latency}ms)`);
      } else {
        toast.error(`${source.name} returned no data`);
      }
    } catch (error: any) {
      const result: TestResult = {
        sourceId,
        sourceName: source.name,
        symbol: testSymbol,
        success: false,
        latency: Date.now() - startTime,
        error: error.message || 'Unknown error',
        timestamp: new Date()
      };
      
      setTestResults(prev => [result, ...prev].slice(0, 50));
      toast.error(`${source.name} test failed: ${error.message}`);
    } finally {
      setIsTestingSingle(null);
    }
  };

  // Test all sources
  const testAllSources = async () => {
    setIsTestingAll(true);
    setTestResults([]);
    
    const sources = dataSourceManager.getAllSources();
    
    for (const source of sources) {
      await testSingleSource(source.id);
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setIsTestingAll(false);
    toast.success('All tests completed');
  };

  // Benchmark sources
  const benchmarkSources = async () => {
    setIsBenchmarking(true);
    setBenchmarkResults([]);
    setBenchmarkProgress(0);
    
    const sources = dataSourceManager.getAllSources();
    const iterations = 5;
    const results: Map<string, BenchmarkResult> = new Map();
    
    // Initialize results
    sources.forEach(source => {
      results.set(source.id, {
        sourceId: source.id,
        sourceName: source.name,
        avgLatency: 0,
        minLatency: Infinity,
        maxLatency: 0,
        successRate: 0,
        totalRequests: 0,
        failedRequests: 0
      });
    });
    
    const totalTests = sources.length * iterations;
    let completedTests = 0;
    
    for (const source of sources) {
      const sourceResults = results.get(source.id)!;
      const latencies: number[] = [];
      
      for (let i = 0; i < iterations; i++) {
        const startTime = Date.now();
        
        try {
          const tempManager = Object.create(dataSourceManager);
          tempManager.setActiveSource(source.id);
          const data = await tempManager.fetchData(testSymbol, false);
          
          const latency = Date.now() - startTime;
          
          if (data) {
            latencies.push(latency);
            sourceResults.minLatency = Math.min(sourceResults.minLatency, latency);
            sourceResults.maxLatency = Math.max(sourceResults.maxLatency, latency);
          } else {
            sourceResults.failedRequests++;
          }
        } catch (error) {
          sourceResults.failedRequests++;
        }
        
        sourceResults.totalRequests++;
        completedTests++;
        setBenchmarkProgress((completedTests / totalTests) * 100);
        
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 200));
      }
      
      // Calculate statistics
      if (latencies.length > 0) {
        sourceResults.avgLatency = latencies.reduce((a, b) => a + b, 0) / latencies.length;
        sourceResults.successRate = ((latencies.length / iterations) * 100);
      } else {
        sourceResults.minLatency = 0;
        sourceResults.successRate = 0;
      }
    }
    
    setBenchmarkResults(Array.from(results.values()));
    setIsBenchmarking(false);
    setBenchmarkProgress(100);
    toast.success('Benchmark completed');
  };

  // Export results
  const exportResults = () => {
    const exportData = {
      testResults: testResults.map(r => ({
        ...r,
        timestamp: r.timestamp.toISOString()
      })),
      benchmarkResults,
      exportedAt: new Date().toISOString()
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `api-test-results-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success('Results exported');
  };

  // Clear results
  const clearResults = () => {
    setTestResults([]);
    setBenchmarkResults([]);
    toast.success('Results cleared');
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          API Testing & Benchmarking
        </Typography>
        
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={clearResults}
          >
            Clear Results
          </Button>
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            onClick={exportResults}
            disabled={testResults.length === 0 && benchmarkResults.length === 0}
          >
            Export Results
          </Button>
        </Box>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                label="Test Symbol"
                value={testSymbol}
                onChange={(e) => setTestSymbol(e.target.value)}
                helperText="ETF code to test (e.g., 510300)"
              />
            </Grid>
            
            <Grid item xs={12} md={8}>
              <Box display="flex" gap={2}>
                <Button
                  variant="contained"
                  startIcon={isTestingAll ? <StopIcon /> : <PlayArrowIcon />}
                  onClick={testAllSources}
                  disabled={isTestingAll || isBenchmarking}
                >
                  {isTestingAll ? 'Testing...' : 'Test All Sources'}
                </Button>
                
                <Button
                  variant="outlined"
                  startIcon={isBenchmarking ? <StopIcon /> : <TimerIcon />}
                  onClick={benchmarkSources}
                  disabled={isBenchmarking || isTestingAll}
                >
                  {isBenchmarking ? 'Benchmarking...' : 'Run Benchmark'}
                </Button>
              </Box>
            </Grid>
          </Grid>
          
          {isBenchmarking && (
            <Box mt={2}>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Benchmark Progress: {Math.round(benchmarkProgress)}%
              </Typography>
              <LinearProgress variant="determinate" value={benchmarkProgress} />
            </Box>
          )}
        </CardContent>
      </Card>

      <Tabs value={tabValue} onChange={handleTabChange} sx={{ mb: 2 }}>
        <Tab label={`Test Results (${testResults.length})`} />
        <Tab label={`Benchmark Results (${benchmarkResults.length})`} />
        <Tab label="Individual Tests" />
      </Tabs>

      {/* Test Results Tab */}
      {tabValue === 0 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Source</TableCell>
                <TableCell>Symbol</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Latency</TableCell>
                <TableCell>Price</TableCell>
                <TableCell>Change</TableCell>
                <TableCell>Error</TableCell>
                <TableCell>Time</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {testResults.map((result, index) => (
                <TableRow key={index}>
                  <TableCell>{result.sourceName}</TableCell>
                  <TableCell>{result.symbol}</TableCell>
                  <TableCell>
                    {result.success ? (
                      <CheckCircleIcon color="success" fontSize="small" />
                    ) : (
                      <ErrorIcon color="error" fontSize="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={`${result.latency}ms`}
                      color={result.latency < 500 ? 'success' : result.latency < 1000 ? 'warning' : 'error'}
                    />
                  </TableCell>
                  <TableCell>
                    {result.data?.price ? `¥${result.data.price.toFixed(3)}` : '-'}
                  </TableCell>
                  <TableCell>
                    {result.data?.changePercent !== undefined ? (
                      <Chip
                        size="small"
                        label={`${result.data.changePercent.toFixed(2)}%`}
                        color={result.data.changePercent >= 0 ? 'success' : 'error'}
                      />
                    ) : '-'}
                  </TableCell>
                  <TableCell>
                    {result.error && (
                      <Typography variant="caption" color="error">
                        {result.error}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>{result.timestamp.toLocaleTimeString()}</TableCell>
                </TableRow>
              ))}
              
              {testResults.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography variant="body2" color="text.secondary">
                      No test results yet. Click "Test All Sources" to begin.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Benchmark Results Tab */}
      {tabValue === 1 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Source</TableCell>
                <TableCell>Success Rate</TableCell>
                <TableCell>Avg Latency</TableCell>
                <TableCell>Min Latency</TableCell>
                <TableCell>Max Latency</TableCell>
                <TableCell>Total Requests</TableCell>
                <TableCell>Failed</TableCell>
                <TableCell>Grade</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {benchmarkResults
                .sort((a, b) => b.successRate - a.successRate || a.avgLatency - b.avgLatency)
                .map((result, index) => {
                  const grade = result.successRate === 100 && result.avgLatency < 500 ? 'A' :
                               result.successRate >= 80 && result.avgLatency < 1000 ? 'B' :
                               result.successRate >= 60 ? 'C' : 
                               result.successRate >= 40 ? 'D' : 'F';
                  
                  return (
                    <TableRow key={result.sourceId}>
                      <TableCell>
                        <Box display="flex" alignItems="center" gap={1}>
                          {index === 0 && <Chip size="small" label="Best" color="success" />}
                          {result.sourceName}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box display="flex" alignItems="center" gap={1}>
                          <LinearProgress
                            variant="determinate"
                            value={result.successRate}
                            sx={{ width: 60, height: 6 }}
                            color={result.successRate >= 80 ? 'success' : result.successRate >= 60 ? 'warning' : 'error'}
                          />
                          <Typography variant="body2">
                            {result.successRate.toFixed(0)}%
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={`${Math.round(result.avgLatency)}ms`}
                          color={result.avgLatency < 500 ? 'success' : result.avgLatency < 1000 ? 'warning' : 'error'}
                        />
                      </TableCell>
                      <TableCell>{Math.round(result.minLatency)}ms</TableCell>
                      <TableCell>{Math.round(result.maxLatency)}ms</TableCell>
                      <TableCell>{result.totalRequests}</TableCell>
                      <TableCell>
                        {result.failedRequests > 0 && (
                          <Chip size="small" label={result.failedRequests} color="error" />
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={grade}
                          size="small"
                          color={grade === 'A' ? 'success' : grade === 'B' ? 'primary' : grade === 'C' ? 'warning' : 'error'}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              
              {benchmarkResults.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8} align="center">
                    <Typography variant="body2" color="text.secondary">
                      No benchmark results yet. Click "Run Benchmark" to test all sources.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Individual Tests Tab */}
      {tabValue === 2 && (
        <Grid container spacing={2}>
          {dataSourceManager.getAllSources().map((source) => (
            <Grid item xs={12} md={6} lg={4} key={source.id}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6">{source.name}</Typography>
                    <Chip
                      size="small"
                      label={source.type === 'free' ? 'Free' : 'Paid'}
                      color={source.type === 'free' ? 'success' : 'warning'}
                    />
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Rate Limit: {source.rateLimit || 'None'}
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Endpoint: {source.endpoint}
                  </Typography>
                  
                  <Box mt={2}>
                    <Button
                      fullWidth
                      variant="outlined"
                      startIcon={isTestingSingle === source.id ? <CircularProgress size={16} /> : <PlayArrowIcon />}
                      onClick={() => testSingleSource(source.id)}
                      disabled={isTestingSingle === source.id || isTestingAll || isBenchmarking}
                    >
                      {isTestingSingle === source.id ? 'Testing...' : 'Test'}
                    </Button>
                  </Box>
                  
                  {/* Show last test result for this source */}
                  {(() => {
                    const lastResult = testResults.find(r => r.sourceId === source.id);
                    if (lastResult) {
                      return (
                        <Box mt={2}>
                          <Alert severity={lastResult.success ? 'success' : 'error'}>
                            <Typography variant="caption">
                              {lastResult.success ? 
                                `Success: ${lastResult.latency}ms` : 
                                `Failed: ${lastResult.error}`}
                            </Typography>
                          </Alert>
                        </Box>
                      );
                    }
                    return null;
                  })()}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
};

export default APITest;