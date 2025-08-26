import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  LinearProgress,
  Chip,
  Button,
  Grid,
  Alert,
  CircularProgress,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';
import { format, addDays } from 'date-fns';
import api from '../../services/api';
import { Holding, DCASchedule } from '../../types';
import { chartColors } from '../../styles/theme';

interface RebalancingStatus {
  required: boolean;
  maxDeviation: number;
  etfsToRebalance: string[];
}

interface RebalanceSuggestion {
  code: string;
  name: string;
  currentWeight: number;
  targetWeight: number;
  deviation: number;
  action: 'BUY' | 'SELL' | 'HOLD';
  shares?: number;
  amount?: number;
}

const CoreModule: React.FC = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ma200SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const [showRebalanceSuggestions, setShowRebalanceSuggestions] = useState(false);
  const [totalPortfolioValue] = useState(100000); // Default portfolio value

  // Helper function to format currency with thousand separators
  const formatCurrency = (value: number): string => {
    return `¥${value.toLocaleString('zh-CN', { 
      minimumFractionDigits: 0,
      maximumFractionDigits: 0 
    })}`;
  };

  // Helper function to format percentage with 1 decimal
  const formatPercentage = (value: number): string => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
  };

  // Fetch holdings
  const { data: holdings, isLoading: holdingsLoading, refetch: refetchHoldings } = useQuery({
    queryKey: ['holdings'],
    queryFn: api.portfolio.getHoldings,
    refetchInterval: 60000, // Refresh every minute
  });

  // Fetch HS300 chart data
  const { data: hs300Data, isLoading: chartLoading } = useQuery({
    queryKey: ['hs300Chart'],
    queryFn: () => api.market.getHS300Chart('6M'),
    refetchInterval: 300000, // Refresh every 5 minutes
  });

  // Fetch DCA schedule
  const { data: dcaSchedule, isLoading: dcaLoading } = useQuery({
    queryKey: ['dcaSchedule'],
    queryFn: api.portfolio.getDCASchedule,
  });

  // Calculate rebalancing status
  const rebalancingStatus: RebalancingStatus = React.useMemo(() => {
    if (!holdings) {
      return { required: false, maxDeviation: 0, etfsToRebalance: [] };
    }

    const deviations = holdings.map(h => Math.abs(h.deviation));
    const maxDeviation = Math.max(...deviations);
    const etfsToRebalance = holdings
      .filter(h => Math.abs(h.deviation) > 2) // Changed threshold to ±2pp as per requirements
      .map(h => h.code);

    return {
      required: maxDeviation > 2,
      maxDeviation,
      etfsToRebalance,
    };
  }, [holdings]);

  // Calculate rebalancing suggestions
  const rebalanceSuggestions: RebalanceSuggestion[] = React.useMemo(() => {
    if (!holdings) return [];

    return holdings
      .filter(h => Math.abs(h.deviation) > 2) // Only suggest for deviations > ±2pp
      .map(holding => {
        const targetValue = totalPortfolioValue * (holding.targetWeight / 100);
        const currentValue = totalPortfolioValue * (holding.currentWeight / 100);
        const differenceValue = targetValue - currentValue;
        const shares = Math.round(Math.abs(differenceValue) / (holding.value / holding.shares));
        
        return {
          code: holding.code,
          name: holding.name,
          currentWeight: holding.currentWeight,
          targetWeight: holding.targetWeight,
          deviation: holding.deviation,
          action: (differenceValue > 0 ? 'BUY' : differenceValue < 0 ? 'SELL' : 'HOLD') as 'BUY' | 'SELL' | 'HOLD',
          shares,
          amount: Math.abs(differenceValue)
        };
      })
      .filter(s => s.action !== 'HOLD');
  }, [holdings, totalPortfolioValue]);

  // Calculate annual line metrics
  const annualLineMetrics = React.useMemo(() => {
    if (!hs300Data || !hs300Data.prices || !hs300Data.ma200) {
      return { deviation: 0, status: 'unknown', unlockDate: null };
    }

    const latestPrice = hs300Data.prices[hs300Data.prices.length - 1];
    const latestMA200 = hs300Data.ma200[hs300Data.ma200.length - 1];
    
    if (!latestPrice || !latestMA200) {
      return { deviation: 0, status: 'unknown', unlockDate: null };
    }

    const deviation = ((latestPrice.value - latestMA200.value) / latestMA200.value) * 100;
    
    // Check for annual line unlock conditions
    let consecutiveDaysAbove = 0;
    for (let i = hs300Data.prices.length - 1; i >= Math.max(0, hs300Data.prices.length - 5); i--) {
      const price = hs300Data.prices[i];
      const ma200 = hs300Data.ma200.find((m: any) => m.time === price.time);
      if (ma200 && price.value > ma200.value) {
        consecutiveDaysAbove++;
      } else {
        break;
      }
    }

    const status = consecutiveDaysAbove >= 5 && deviation >= 1 ? 'unlocked' : 'locked';
    
    return {
      deviation,
      status,
      consecutiveDaysAbove,
      unlockDate: status === 'unlocked' ? new Date() : null
    };
  }, [hs300Data]);

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current || !hs300Data) return;

    // Create chart
    chartRef.current = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 400,
      layout: {
        background: { color: 'transparent' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#e0e0e0' },
        horzLines: { color: '#e0e0e0' },
      },
      crosshair: {
        mode: 1, // Magnet mode
      },
      rightPriceScale: {
        borderColor: '#e0e0e0',
      },
      timeScale: {
        borderColor: '#e0e0e0',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Add HS300 series
    seriesRef.current = chartRef.current.addLineSeries({
      color: chartColors.primary[0],
      lineWidth: 2,
      title: 'HS300',
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    });

    // Add MA200 series
    ma200SeriesRef.current = chartRef.current.addLineSeries({
      color: chartColors.warning[1],
      lineWidth: 2,
      lineStyle: 2, // Dashed
      title: 'MA200',
      priceFormat: {
        type: 'price',
        precision: 2,
        minMove: 0.01,
      },
    });

    // Set data
    if (hs300Data.prices) {
      seriesRef.current.setData(hs300Data.prices);
      
      // Add markers for annual line events
      const markers = [];
      
      // Check for unlock/lock events
      for (let i = 5; i < hs300Data.prices.length; i++) {
        const price = hs300Data.prices[i];
        const ma200 = hs300Data.ma200.find((m: any) => m.time === price.time);
        
        if (ma200) {
          const deviation = ((price.value - ma200.value) / ma200.value) * 100;
          
          // Check previous 5 days
          let prevConsecutive = 0;
          for (let j = i - 1; j >= Math.max(0, i - 5); j--) {
            const prevPrice = hs300Data.prices[j];
            const prevMA200 = hs300Data.ma200.find((m: any) => m.time === prevPrice.time);
            if (prevMA200 && prevPrice.value > prevMA200.value) {
              prevConsecutive++;
            } else {
              break;
            }
          }
          
          // Mark unlock events
          if (prevConsecutive >= 4 && price.value > ma200.value && deviation >= 1) {
            markers.push({
              time: price.time,
              position: 'belowBar' as const,
              color: '#4caf50',
              shape: 'arrowUp' as const,
              text: '年线解锁',
            });
          }
          
          // Mark falling below events
          if (i > 0 && hs300Data.prices[i - 1].value > hs300Data.ma200[i - 1].value && price.value <= ma200.value) {
            markers.push({
              time: price.time,
              position: 'aboveBar' as const,
              color: '#f44336',
              shape: 'arrowDown' as const,
              text: '年线回落',
            });
          }
        }
      }
      
      if (markers.length > 0) {
        seriesRef.current.setMarkers(markers);
      }
    }
    if (hs300Data.ma200) {
      ma200SeriesRef.current.setData(hs300Data.ma200);
    }

    // Handle resize
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [hs300Data]);

  const handleRebalance = async () => {
    try {
      await api.portfolio.rebalance();
      refetchHoldings();
    } catch (error) {
      console.error('Rebalance error:', error);
    }
  };

  const getDeviationColor = (deviation: number): string => {
    const abs = Math.abs(deviation);
    if (abs <= 2) return 'success';
    if (abs <= 5) return 'warning';
    return 'error';
  };

  const renderDeviationBar = (deviation: number) => {
    const abs = Math.abs(deviation);
    const color = getDeviationColor(deviation);
    
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Box sx={{ flex: 1, minWidth: 100 }}>
          <LinearProgress
            variant="determinate"
            value={Math.min(abs * 10, 100)} // Scale for visibility
            color={color as any}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>
        <Typography 
          variant="body2" 
          color={`${color}.main`}
          fontWeight={600}
          sx={{ minWidth: 50, textAlign: 'right' }}
        >
          {formatPercentage(deviation)}
        </Typography>
      </Box>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Core模块
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant={rebalancingStatus.required ? 'contained' : 'outlined'}
            color={rebalancingStatus.required ? 'warning' : 'primary'}
            startIcon={rebalancingStatus.required ? <WarningIcon /> : <TrendingUpIcon />}
            onClick={() => setShowRebalanceSuggestions(!showRebalanceSuggestions)}
          >
            {rebalancingStatus.required ? `回到目标 ±2pp (${rebalancingStatus.etfsToRebalance.length}只)` : '组合已平衡'}
          </Button>
          <Tooltip title="刷新">
            <IconButton onClick={() => refetchHoldings()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Holdings Table */}
        <Grid item xs={12} lg={7}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight={600}>
                当前持仓
              </Typography>
              
              {holdingsLoading ? (
                <Box display="flex" justifyContent="center" py={3}>
                  <CircularProgress />
                </Box>
              ) : holdings && holdings.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>代码</TableCell>
                        <TableCell>名称</TableCell>
                        <TableCell align="right">目标权重</TableCell>
                        <TableCell align="right">当前权重</TableCell>
                        <TableCell>偏差</TableCell>
                        <TableCell align="right">溢价率</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {holdings.map((holding) => (
                        <TableRow key={holding.code}>
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>
                              {holding.code}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {holding.name}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">
                              {holding.targetWeight.toFixed(1)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">
                              {holding.currentWeight.toFixed(1)}%
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {renderDeviationBar(holding.deviation)}
                          </TableCell>
                          <TableCell align="right">
                            {holding.code === '513500' && holding.premium !== undefined ? (
                              <Chip
                                label={`${holding.premium.toFixed(1)}%`}
                                size="small"
                                color={holding.premium <= 2 ? 'success' : 'warning'}
                              />
                            ) : (
                              '-'
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info">暂无持仓数据</Alert>
              )}

              {/* Rebalancing Suggestions */}
              {showRebalanceSuggestions && rebalanceSuggestions.length > 0 && (
                <Box mt={2}>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" fontWeight={600} gutterBottom>
                      再平衡建议 (回到目标±2pp)
                    </Typography>
                    <Typography variant="caption">
                      最大偏差：{rebalancingStatus.maxDeviation.toFixed(1)}% | 
                      需调整：{rebalancingStatus.etfsToRebalance.length}只ETF
                    </Typography>
                  </Alert>
                  
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>ETF</TableCell>
                          <TableCell>操作</TableCell>
                          <TableCell align="right">股数</TableCell>
                          <TableCell align="right">金额</TableCell>
                          <TableCell>权重变化</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {rebalanceSuggestions.map((suggestion) => (
                          <TableRow key={suggestion.code}>
                            <TableCell>
                              <Box>
                                <Typography variant="body2" fontWeight={600}>
                                  {suggestion.code}
                                </Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {suggestion.name}
                                </Typography>
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={suggestion.action === 'BUY' ? '买入' : '卖出'}
                                size="small"
                                color={suggestion.action === 'BUY' ? 'success' : 'error'}
                              />
                            </TableCell>
                            <TableCell align="right">
                              {suggestion.shares?.toLocaleString() || '-'}
                            </TableCell>
                            <TableCell align="right">
                              {suggestion.amount ? formatCurrency(suggestion.amount) : '-'}
                            </TableCell>
                            <TableCell>
                              <Typography variant="caption">
                                {suggestion.currentWeight.toFixed(1)}% → {suggestion.targetWeight.toFixed(1)}%
                              </Typography>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                  
                  <Box mt={2} display="flex" justifyContent="flex-end" gap={2}>
                    <Button 
                      variant="outlined" 
                      onClick={() => setShowRebalanceSuggestions(false)}
                    >
                      关闭建议
                    </Button>
                    <Button 
                      variant="contained" 
                      color="primary"
                      onClick={handleRebalance}
                    >
                      执行再平衡
                    </Button>
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Right Column */}
        <Grid item xs={12} lg={5}>
          <Grid container spacing={3}>
            {/* DCA Schedule */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <ScheduleIcon color="primary" />
                    <Typography variant="h6" fontWeight={600}>
                      定投计划
                    </Typography>
                  </Box>

                  {dcaLoading ? (
                    <CircularProgress size={20} />
                  ) : dcaSchedule ? (
                    <Box>
                      {/* Main status line */}
                      <Alert severity="info" sx={{ mb: 2 }}>
                        <Typography variant="body2" fontWeight={600}>
                          下次定投：{format(new Date(dcaSchedule.nextDate), 'MMM dd, yyyy')} | 窗口 10:30/14:00 (CST) | 状态：{dcaSchedule.enabled ? '已启用' : '已暂停'}
                        </Typography>
                      </Alert>

                      {/* Execution window info */}
                      <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          执行窗口
                        </Typography>
                        <Typography variant="body1" fontWeight={600}>
                          下次窗口 10:30 / 14:00 (CST)
                        </Typography>
                      </Box>

                      {/* QDII Threshold Warning */}
                      <Alert severity="warning" sx={{ mb: 2 }}>
                        <Typography variant="caption">
                          <strong>QDII 门槛提示：</strong>513500 若溢价&gt;2% 将自动停放 511990
                        </Typography>
                      </Alert>

                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            定投金额
                          </Typography>
                          <Typography variant="h6" fontWeight={600}>
                            {formatCurrency(dcaSchedule.amount)}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            定投频率
                          </Typography>
                          <Chip 
                            label={dcaSchedule.frequency === 'MONTHLY' ? '每月' : dcaSchedule.frequency} 
                            size="small" 
                            color="primary"
                          />
                        </Grid>
                      </Grid>

                      {/* Annual line unlock status */}
                      <Box sx={{ mt: 2, p: 2, bgcolor: 'success.50', borderRadius: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          年线解锁状态
                        </Typography>
                        <Typography variant="body2" fontWeight={600}>
                          年线解锁：满足 连续5日在上 + 收盘≥+1% (8/23)
                        </Typography>
                      </Box>
                    </Box>
                  ) : (
                    <Alert severity="info">尚未配置定投计划</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* HS300 Chart */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="h6" fontWeight={600}>
                      沪深300指数与200日均线
                    </Typography>
                    {annualLineMetrics.deviation !== 0 && (
                      <Chip
                        label={`收盘-年线 = ${formatPercentage(annualLineMetrics.deviation)}`}
                        color={annualLineMetrics.deviation >= 0 ? 'success' : 'error'}
                        size="small"
                      />
                    )}
                  </Box>

                  {/* Annual line status alert */}
                  {annualLineMetrics.status === 'unlocked' && (
                    <Alert severity="success" sx={{ mb: 2 }}>
                      <Typography variant="body2">
                        <strong>年线解锁已触发</strong> - 连续{annualLineMetrics.consecutiveDaysAbove}日在上 + 收盘≥+1%
                      </Typography>
                    </Alert>
                  )}
                  
                  <Box 
                    ref={chartContainerRef} 
                    sx={{ 
                      width: '100%', 
                      height: 400,
                      position: 'relative',
                    }}
                  >
                    {chartLoading && (
                      <Box 
                        sx={{ 
                          position: 'absolute',
                          top: '50%',
                          left: '50%',
                          transform: 'translate(-50%, -50%)',
                        }}
                      >
                        <CircularProgress />
                      </Box>
                    )}
                  </Box>

                  {/* Additional metrics below chart */}
                  {hs300Data && (
                    <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
                      <Typography variant="caption" color="text.secondary">
                        最新收盘：{hs300Data.prices?.[hs300Data.prices.length - 1]?.value.toFixed(2)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        200日均线：{hs300Data.ma200?.[hs300Data.ma200.length - 1]?.value.toFixed(2)}
                      </Typography>
                      <Typography 
                        variant="caption" 
                        color={annualLineMetrics.deviation >= 0 ? 'success.main' : 'error.main'}
                        fontWeight={600}
                      >
                        偏离：{formatPercentage(annualLineMetrics.deviation)}
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default CoreModule;