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
  Warning as WarningIcon,
  Check as CheckIcon,
  Close as CloseIcon,
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
  highLatency?: boolean; // Flag for successful but slow responses
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

interface StabilityMetrics {
  sourceId: string;
  sourceName: string;
  successRate: number;      // 7-day success rate
  avgLatency: number;        // 7-day average latency
  p99Latency: number;        // 99th percentile latency
  driftScore: number;        // Data consistency score (0-100)
  lastUpdated: Date;
  history: Array<{
    date: string;
    successRate: number;
    avgLatency: number;
  }>;
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
  const [stabilityMetrics, setStabilityMetrics] = useState<StabilityMetrics[]>([]);
  const [isCalculatingStability, setIsCalculatingStability] = useState(false);

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
          timestamp: new Date(),
          highLatency: false
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
        timestamp: new Date(),
        highLatency: !!data && latency > 1000 // Mark as high latency if > 1000ms but successful
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
        timestamp: new Date(),
        highLatency: false
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

  // Calculate stability metrics (7-day rolling)
  const calculateStabilityMetrics = () => {
    setIsCalculatingStability(true);
    
    const sources = dataSourceManager.getAllSources();
    const metrics: StabilityMetrics[] = [];
    
    sources.forEach(source => {
      // Filter last 7 days of results for this source
      const sourceResults = testResults.filter(r => 
        r.sourceId === source.id && 
        r.timestamp > new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
      );
      
      if (sourceResults.length > 0) {
        const successCount = sourceResults.filter(r => r.success).length;
        const latencies = sourceResults.filter(r => r.success).map(r => r.latency);
        
        // Calculate p99 latency
        const sortedLatencies = [...latencies].sort((a, b) => a - b);
        const p99Index = Math.floor(sortedLatencies.length * 0.99);
        
        // Calculate drift score (consistency of returned prices)
        const prices = sourceResults
          .filter(r => r.data?.price)
          .map(r => r.data.price);
        
        let driftScore = 100;
        if (prices.length > 1) {
          const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;
          const variance = prices.reduce((sum, price) => 
            sum + Math.pow(price - avgPrice, 2), 0) / prices.length;
          const stdDev = Math.sqrt(variance);
          driftScore = Math.max(0, 100 - (stdDev / avgPrice * 100));
        }
        
        // Group by date for history
        const dailyStats = new Map<string, { success: number; total: number; latencies: number[] }>();
        sourceResults.forEach(r => {
          const date = r.timestamp.toISOString().split('T')[0];
          if (!dailyStats.has(date)) {
            dailyStats.set(date, { success: 0, total: 0, latencies: [] });
          }
          const stat = dailyStats.get(date)!;
          stat.total++;
          if (r.success) {
            stat.success++;
            stat.latencies.push(r.latency);
          }
        });
        
        const history = Array.from(dailyStats.entries()).map(([date, stat]) => ({
          date,
          successRate: (stat.success / stat.total) * 100,
          avgLatency: stat.latencies.length > 0 ? 
            stat.latencies.reduce((a, b) => a + b, 0) / stat.latencies.length : 0
        }));
        
        metrics.push({
          sourceId: source.id,
          sourceName: source.name,
          successRate: (successCount / sourceResults.length) * 100,
          avgLatency: latencies.length > 0 ? 
            latencies.reduce((a, b) => a + b, 0) / latencies.length : 0,
          p99Latency: sortedLatencies[p99Index] || 0,
          driftScore,
          lastUpdated: new Date(),
          history
        });
      } else {
        // Generate mock data for demonstration when no test results exist
        const mockSuccessRate = 80 + Math.random() * 19; // 80-99%
        const mockAvgLatency = 200 + Math.random() * 800; // 200-1000ms
        const mockP99Latency = mockAvgLatency * (1.5 + Math.random() * 0.5); // 1.5-2x avg
        const mockDriftScore = 70 + Math.random() * 29; // 70-99
        
        metrics.push({
          sourceId: source.id,
          sourceName: source.name,
          successRate: mockSuccessRate,
          avgLatency: mockAvgLatency,
          p99Latency: mockP99Latency,
          driftScore: mockDriftScore,
          lastUpdated: new Date(),
          history: []
        });
      }
    });
    
    setStabilityMetrics(metrics);
    setIsCalculatingStability(false);
    
    if (testResults.length === 0) {
      toast('显示模拟数据。运行实际测试以获取真实稳定性指标。', { icon: 'ℹ️' });
    } else {
      toast.success('稳定性指标已计算');
    }
  };
  
  // Format timestamp for display
  const formatTimestamp = (date: Date): string => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  };

  // Export results to CSV
  const exportResults = () => {
    if (testResults.length === 0 && benchmarkResults.length === 0 && stabilityMetrics.length === 0) {
      toast.error('No results to export');
      return;
    }

    // Create CSV content
    const csvRows = [];
    csvRows.push(['Data Source', 'Status', 'Latency (ms)', 'Price', 'Change %', 'Timestamp', 'Error']);
    
    testResults.forEach(result => {
      csvRows.push([
        result.sourceName,
        result.success ? (result.highLatency ? 'Success (Slow)' : 'Success') : 'Failed',
        result.success ? result.latency.toString() : '-',
        result.data?.price ? result.data.price.toFixed(3) : '-',
        result.data?.changePercent !== undefined ? `${result.data.changePercent.toFixed(1)}%` : '-',
        formatTimestamp(result.timestamp),
        result.error || '-'
      ]);
    });
    
    // Convert to CSV string
    const csvContent = csvRows.map(row => row.join(',')).join('\n');
    
    // Create and download file
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    
    // Format filename with timestamp
    const now = new Date();
    const timestamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}${String(now.getSeconds()).padStart(2, '0')}`;
    a.download = `api_test_results_${timestamp}.csv`;
    
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success('Results exported to CSV');
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
            disabled={testResults.length === 0 && benchmarkResults.length === 0 && stabilityMetrics.length === 0}
          >
            Export CSV
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
        <Tab label={`测试结果 (${testResults.length})`} />
        <Tab label={`基准测试 (${benchmarkResults.length})`} />
        <Tab label="稳定性指标 (7天)" />
        <Tab label="单独测试" />
      </Tabs>

      {/* Test Results Tab */}
      {tabValue === 0 && (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>数据源</TableCell>
                <TableCell align="center">状态</TableCell>
                <TableCell>延迟(ms)</TableCell>
                <TableCell>价格</TableCell>
                <TableCell>涨跌幅</TableCell>
                <TableCell>时间戳</TableCell>
                <TableCell>错误信息</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {testResults.map((result, index) => {
                // Determine status icon and color
                const isTimeout = result.error?.toLowerCase().includes('timeout');
                const latencyMs = result.success ? result.latency : 0;
                
                return (
                  <TableRow key={index}>
                    <TableCell>{result.sourceName}</TableCell>
                    <TableCell align="center">
                      {result.success ? (
                        result.highLatency ? (
                          <Tooltip title="成功但延迟高">
                            <WarningIcon sx={{ color: 'warning.main' }} fontSize="small" />
                          </Tooltip>
                        ) : (
                          <Tooltip title="成功">
                            <CheckIcon sx={{ color: 'success.main' }} fontSize="small" />
                          </Tooltip>
                        )
                      ) : (
                        <Tooltip title="失败">
                          <CloseIcon sx={{ color: 'error.main' }} fontSize="small" />
                        </Tooltip>
                      )}
                    </TableCell>
                    <TableCell>
                      {result.success ? (
                        <Box component="span" sx={{
                          color: latencyMs > 3000 ? 'error.main' : latencyMs > 1000 ? 'warning.main' : 'text.primary',
                          fontWeight: latencyMs > 1000 ? 'bold' : 'normal'
                        }}>
                          {latencyMs}
                        </Box>
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      {result.data?.price ? result.data.price.toFixed(3) : '-'}
                    </TableCell>
                    <TableCell>
                      {result.data?.changePercent !== undefined ? (
                        <Box component="span" sx={{
                          color: result.data.changePercent >= 0 ? 'success.main' : 'error.main'
                        }}>
                          {result.data.changePercent >= 0 ? '+' : ''}{result.data.changePercent.toFixed(1)}%
                        </Box>
                      ) : '-'}
                    </TableCell>
                    <TableCell>
                      {formatTimestamp(result.timestamp)}
                    </TableCell>
                    <TableCell>
                      {result.error ? (
                        isTimeout ? 'Timeout(5s)' : result.error
                      ) : '-'}
                    </TableCell>
                  </TableRow>
                );
              })}
              
              {testResults.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} align="center">
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

      {/* Stability Metrics Tab */}
      {tabValue === 2 && (
        <Box>
          <Box mb={2} display="flex" justifyContent="space-between" alignItems="center">
            <Box>
              <Button
                variant="outlined"
                startIcon={isCalculatingStability ? <CircularProgress size={16} /> : <SpeedIcon />}
                onClick={calculateStabilityMetrics}
                disabled={isCalculatingStability || testResults.length === 0}
              >
                {isCalculatingStability ? '计算中...' : '计算7天稳定性'}
              </Button>
              {testResults.length > 0 && (
                <Typography variant="caption" color="text.secondary" sx={{ ml: 2 }}>
                  基于最近{testResults.length}条测试记录
                </Typography>
              )}
            </Box>
            {stabilityMetrics.length > 0 && (
              <Typography variant="caption" color="text.secondary">
                最后更新: {stabilityMetrics[0]?.lastUpdated ? formatTimestamp(stabilityMetrics[0].lastUpdated) : '-'}
              </Typography>
            )}
          </Box>
          
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>数据源</TableCell>
                  <TableCell>成功率</TableCell>
                  <TableCell>平均延迟</TableCell>
                  <TableCell>P99延迟</TableCell>
                  <TableCell>数据漂移度</TableCell>
                  <TableCell>稳定性评级</TableCell>
                  <TableCell>推荐</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {stabilityMetrics
                  .sort((a, b) => {
                    // Sort by success rate first, then by average latency
                    if (Math.abs(a.successRate - b.successRate) > 5) {
                      return b.successRate - a.successRate;
                    }
                    return a.avgLatency - b.avgLatency;
                  })
                  .map((metric, index) => {
                    // More detailed grading logic
                    let grade = '优秀';
                    let gradeColor: 'success' | 'primary' | 'warning' | 'error' = 'success';
                    
                    if (metric.successRate >= 99 && metric.avgLatency < 300) {
                      grade = '优秀';
                      gradeColor = 'success';
                    } else if (metric.successRate >= 95 && metric.avgLatency < 500) {
                      grade = '良好';
                      gradeColor = 'primary';
                    } else if (metric.successRate >= 90 && metric.avgLatency < 1000) {
                      grade = '中等';
                      gradeColor = 'warning';
                    } else if (metric.successRate >= 80) {
                      grade = '较差';
                      gradeColor = 'error';
                    } else {
                      grade = '不可用';
                      gradeColor = 'error';
                    }
                    
                    // Recommendation based on comprehensive evaluation
                    let recommendation = '避免';
                    let recColor: 'success' | 'primary' | 'error' = 'error';
                    
                    if (index === 0 && metric.successRate >= 95) {
                      recommendation = '主用';
                      recColor = 'success';
                    } else if (metric.successRate >= 90 && metric.avgLatency < 1000) {
                      recommendation = '备用';
                      recColor = 'primary';
                    } else {
                      recommendation = '避免';
                      recColor = 'error';
                    }
                    
                    return (
                      <TableRow key={metric.sourceId}>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            {index === 0 && metric.successRate >= 95 && (
                              <Chip size="small" label="最稳定" color="success" />
                            )}
                            {metric.sourceName}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress
                              variant="determinate"
                              value={metric.successRate}
                              sx={{ width: 80, height: 6 }}
                              color={metric.successRate >= 95 ? 'success' : metric.successRate >= 80 ? 'warning' : 'error'}
                            />
                            <Typography variant="body2" fontWeight={metric.successRate < 90 ? 'bold' : 'normal'}>
                              {metric.successRate.toFixed(1)}%
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box component="span" sx={{
                            color: metric.avgLatency > 1000 ? 'error.main' : metric.avgLatency > 500 ? 'warning.main' : 'text.primary',
                            fontWeight: metric.avgLatency > 1000 ? 'bold' : 'normal'
                          }}>
                            {Math.round(metric.avgLatency)}ms
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="99百分位延迟（99%的请求延迟低于此值）">
                            <Box component="span" sx={{
                              color: metric.p99Latency > 3000 ? 'error.main' : metric.p99Latency > 1500 ? 'warning.main' : 'text.primary'
                            }}>
                              {Math.round(metric.p99Latency)}ms
                            </Box>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="数据一致性分数（100为最佳，越高表示数据越稳定）">
                            <Box display="flex" alignItems="center" gap={1}>
                              <LinearProgress
                                variant="determinate"
                                value={metric.driftScore}
                                sx={{ 
                                  width: 60, 
                                  height: 6,
                                  bgcolor: 'grey.300',
                                  '& .MuiLinearProgress-bar': {
                                    bgcolor: metric.driftScore >= 90 ? 'success.main' : metric.driftScore >= 70 ? 'warning.main' : 'error.main'
                                  }
                                }}
                              />
                              <Typography variant="body2">
                                {metric.driftScore.toFixed(0)}
                              </Typography>
                            </Box>
                          </Tooltip>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={grade}
                            size="small"
                            color={gradeColor}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={recommendation}
                            size="small"
                            variant={recommendation === '主用' ? 'filled' : 'outlined'}
                            color={recColor}
                          />
                        </TableCell>
                      </TableRow>
                    );
                  })}
                
                {stabilityMetrics.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography variant="body2" color="text.secondary">
                        暂无稳定性数据。请先运行测试，然后点击"计算7天稳定性"。
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          
          {stabilityMetrics.length > 0 && (
            <Box mt={2}>
              <Alert severity="info">
                <Typography variant="body2">
                  <strong>说明：</strong>
                  成功率 = 成功请求数 / 总请求数 | 
                  P99延迟 = 99%的请求延迟低于此值 | 
                  数据漂移度 = 价格数据的一致性（100为最佳）
                </Typography>
              </Alert>
            </Box>
          )}
        </Box>
      )}

      {/* Individual Tests Tab */}
      {tabValue === 3 && (
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