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

const CoreModule: React.FC = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const ma200SeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

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
      .filter(h => Math.abs(h.deviation) > 5)
      .map(h => h.code);

    return {
      required: maxDeviation > 5,
      maxDeviation,
      etfsToRebalance,
    };
  }, [holdings]);

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
          {deviation > 0 ? '+' : ''}{deviation.toFixed(1)}%
        </Typography>
      </Box>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Core Module
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant={rebalancingStatus.required ? 'contained' : 'outlined'}
            color={rebalancingStatus.required ? 'warning' : 'primary'}
            startIcon={rebalancingStatus.required ? <WarningIcon /> : <TrendingUpIcon />}
            onClick={handleRebalance}
            disabled={!rebalancingStatus.required}
          >
            {rebalancingStatus.required ? 'Rebalance Required' : 'Portfolio Balanced'}
          </Button>
          <Tooltip title="Refresh">
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
                Current Holdings
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
                        <TableCell>Code</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell align="right">Target</TableCell>
                        <TableCell align="right">Current</TableCell>
                        <TableCell>Deviation</TableCell>
                        <TableCell align="right">Premium</TableCell>
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
                                label={`${holding.premium.toFixed(2)}%`}
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
                <Alert severity="info">No holdings data available</Alert>
              )}

              {/* Rebalancing Meter */}
              {rebalancingStatus.required && (
                <Alert 
                  severity="warning" 
                  sx={{ mt: 2 }}
                  action={
                    <Button color="inherit" size="small" onClick={handleRebalance}>
                      Rebalance Now
                    </Button>
                  }
                >
                  Maximum deviation: {rebalancingStatus.maxDeviation.toFixed(1)}% 
                  ({rebalancingStatus.etfsToRebalance.length} ETFs need rebalancing)
                </Alert>
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
                      DCA Schedule
                    </Typography>
                  </Box>

                  {dcaLoading ? (
                    <CircularProgress size={20} />
                  ) : dcaSchedule ? (
                    <Box>
                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            Next Investment
                          </Typography>
                          <Typography variant="h6" fontWeight={600}>
                            {format(new Date(dcaSchedule.nextDate), 'MMM dd, yyyy')}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            Amount
                          </Typography>
                          <Typography variant="h6" fontWeight={600}>
                            ¥{dcaSchedule.amount.toLocaleString()}
                          </Typography>
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            Frequency
                          </Typography>
                          <Chip 
                            label={dcaSchedule.frequency} 
                            size="small" 
                            color="primary"
                          />
                        </Grid>
                        <Grid item xs={6}>
                          <Typography variant="body2" color="text.secondary">
                            Status
                          </Typography>
                          <Chip 
                            label={dcaSchedule.enabled ? 'Active' : 'Paused'} 
                            size="small" 
                            color={dcaSchedule.enabled ? 'success' : 'default'}
                          />
                        </Grid>
                      </Grid>
                    </Box>
                  ) : (
                    <Alert severity="info">No DCA schedule configured</Alert>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* HS300 Chart */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    HS300 Index with MA200
                  </Typography>
                  
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