import React, { useState, useMemo, useEffect } from 'react';
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
  Chip,
  Button,
  Grid,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  FormControl,
  Select,
  MenuItem,
  Stack,
  Divider,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  RotateRight as RotateIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  FilterList as FilterIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format, endOfMonth, isEqual, differenceInDays } from 'date-fns';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { MomentumETF, CorrelationMatrix, CorrelationItem } from '../../types';
import { chartColors } from '../../styles/theme';

interface FilterOptions {
  growth: 'none' | string;
  newEnergy: 'none' | string;
}

interface EnhancedMomentumETF extends Omit<MomentumETF, 'volume'> {
  correlationWithTop1: number;
  bufferDiff: number;
  minHoldingDaysRemaining: number;
  volume: number; // 成交额（亿元）
}

interface QualificationDetail {
  bufferPass: boolean;
  bufferValue: number;
  bufferThreshold: number;
  minHoldingPass: boolean;
  minHoldingDaysRemaining: number;
  minHoldingThreshold: number;
  correlationPass: boolean;
  correlationValue: number;
  correlationThreshold: number;
  legLimitPass: boolean;
  currentLegCount: number;
  maxLegCount: number;
  overallPass: boolean;
}

const SatelliteModuleEnhanced: React.FC = () => {
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    growth: 'none',
    newEnergy: 'none',
  });
  const [selectedETF, setSelectedETF] = useState<string | null>(null);
  const [qualificationDetails, setQualificationDetails] = useState<QualificationDetail | null>(null);

  const today = new Date();
  const isMonthEnd = isEqual(today, endOfMonth(today));

  // Fetch momentum rankings
  const { 
    data: momentumData, 
    isLoading: rankingsLoading, 
    refetch: refetchRankings 
  } = useQuery({
    queryKey: ['momentumRankings'],
    queryFn: api.market.getMomentumRankings,
    refetchInterval: 300000, // Refresh every 5 minutes
  });

  // Fetch correlation matrix - ONLY for satellite candidates
  const { 
    data: correlationData, 
    isLoading: correlationLoading 
  } = useQuery({
    queryKey: ['correlationMatrix', momentumData?.[0]?.code],
    queryFn: () => api.market.getCorrelationMatrix(momentumData![0].code),
    enabled: !!momentumData && momentumData.length > 0,
  });

  // Calculate qualification details based on current holdings and candidates
  useEffect(() => {
    if (momentumData && momentumData.length > 0) {
      const top1 = momentumData[0];
      const currentHolding = momentumData.find(etf => etf.isHolding);
      
      // Calculate qualification criteria
      const bufferThreshold = 3; // 3% buffer
      const minHoldingDays = 28; // 4 weeks minimum
      const correlationThreshold = 0.8;
      const maxLegs = 2;
      
      // Get correlation with Top1 (excluding 510300 core)
      // Filter out 510300 from satellite candidates
      const satelliteCandidates = momentumData.filter(etf => etf.code !== '510300');
      const satelliteTop1 = satelliteCandidates[0]; // Top1 among satellites only
      
      // Get correlation with Top1
      const correlationWithTop1 = correlationData?.correlations?.find(
        (c: CorrelationItem) => 
          ((c.etf1 === satelliteTop1.code && c.etf2 === currentHolding?.code) ||
           (c.etf1 === currentHolding?.code && c.etf2 === satelliteTop1.code))
      )?.correlation || 0;
      
      // Calculate buffer difference: score_new - score_hold
      const bufferDiff = currentHolding ? 
        satelliteTop1.score - currentHolding.score : 
        0;
      
      // Calculate minimum holding days remaining
      const holdingStartDate = currentHolding?.holdingStartDate;
      const daysHeld = holdingStartDate ? 
        differenceInDays(today, new Date(holdingStartDate)) : 0;
      const daysRemaining = currentHolding ? 
        Math.max(0, minHoldingDays - daysHeld) : 0;
      
      const details: QualificationDetail = {
        bufferPass: bufferDiff >= bufferThreshold,
        bufferValue: bufferDiff,
        bufferThreshold,
        minHoldingPass: daysRemaining === 0,
        minHoldingDaysRemaining: daysRemaining,
        minHoldingThreshold: minHoldingDays,
        correlationPass: correlationWithTop1 <= correlationThreshold,
        correlationValue: correlationWithTop1,
        correlationThreshold,
        legLimitPass: true, // Always true for now, implement leg counting logic
        currentLegCount: 1,
        maxLegCount: maxLegs,
        overallPass: false,
      };
      
      // Overall pass = ALL criteria must pass (AND logic)
      details.overallPass = 
        details.bufferPass && 
        details.minHoldingPass && 
        details.correlationPass && 
        details.legLimitPass;
      
      setQualificationDetails(details);
    }
  }, [momentumData, correlationData, today]);

  // Rotation mutation
  const rotationMutation = useMutation({
    mutationFn: () => api.portfolio.rebalance(),
    onSuccess: () => {
      toast.success('组合轮动完成');
      refetchRankings();
    },
    onError: (error) => {
      toast.error('组合轮动失败');
      console.error('Rotation error:', error);
    },
  });

  // Apply filters to momentum data
  const filteredMomentumData = useMemo(() => {
    if (!momentumData) return [];

    let filtered = [...momentumData];

    // Apply growth filter (max 1)
    if (filterOptions.growth !== 'none') {
      const growthETFs = filtered.filter(etf => etf.type === 'Growth');
      const selectedGrowth = growthETFs.find(etf => etf.code === filterOptions.growth);
      if (selectedGrowth) {
        filtered = filtered.filter(etf => 
          etf.type !== 'Growth' || etf.code === filterOptions.growth
        );
      }
    }

    // Apply new energy filter (max 1)
    if (filterOptions.newEnergy !== 'none') {
      const newEnergyETFs = filtered.filter(etf => etf.type === 'NewEnergy');
      const selectedNewEnergy = newEnergyETFs.find(etf => etf.code === filterOptions.newEnergy);
      if (selectedNewEnergy) {
        filtered = filtered.filter(etf => 
          etf.type !== 'NewEnergy' || etf.code === filterOptions.newEnergy
        );
      }
    }

    return filtered;
  }, [momentumData, filterOptions]);

  // Calculate correlation with Top1 for each ETF
  const enhancedMomentumData = useMemo((): EnhancedMomentumETF[] => {
    if (!filteredMomentumData || filteredMomentumData.length === 0) return [];
    
    // Filter out 510300 (Core) from satellite candidates
    const satelliteData = filteredMomentumData.filter(etf => etf.code !== '510300');
    const top1 = satelliteData[0]; // Top1 among satellites only
    const currentHolding = satelliteData.find(etf => etf.isHolding);
    
    return satelliteData.map(etf => {
      // Get correlation with Top1
      const correlationWithTop1 = etf.code === top1.code ? 1.0 :
        correlationData?.correlations?.find(
          (c: CorrelationItem) => (c.etf1 === top1.code && c.etf2 === etf.code) ||
               (c.etf1 === etf.code && c.etf2 === top1.code)
        )?.correlation || 0;
      
      // Calculate buffer difference: score_new - score_hold
      const bufferDiff = currentHolding ? 
        etf.score - currentHolding.score : 
        0;
      
      // Calculate minimum holding days remaining
      const holdingStartDate = etf.isHolding ? etf.holdingStartDate : null;
      const daysHeld = holdingStartDate ? 
        differenceInDays(today, new Date(holdingStartDate)) : 0;
      const minHoldingDaysRemaining = etf.isHolding ? 
        Math.max(0, 28 - daysHeld) : 0;
      
      // Add mock volume data (成交额) - this should come from API
      const volume = Math.random() * 50 + 10; // Mock: 10-60亿元
      
      return {
        ...etf,
        correlationWithTop1,
        bufferDiff,
        minHoldingDaysRemaining,
        volume,
      };
    });
  }, [filteredMomentumData, correlationData, today]);

  const renderCorrelationHeatmap = () => {
    if (!correlationData || !enhancedMomentumData) return null;

    const top5 = enhancedMomentumData.slice(0, 5);
    
    return (
      <Box>
        <TableContainer component={Paper} variant="outlined">
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell></TableCell>
                {top5.map(etf => (
                  <TableCell key={etf.code} align="center">
                    <Typography variant="caption" fontWeight={600}>
                      {etf.code}
                    </Typography>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {top5.map(etf1 => (
                <TableRow key={etf1.code}>
                  <TableCell>
                    <Typography variant="caption" fontWeight={600}>
                      {etf1.name}
                    </Typography>
                  </TableCell>
                  {top5.map(etf2 => {
                    const correlation = correlationData.correlations?.find(
                      (c: CorrelationItem) => (c.etf1 === etf1.code && c.etf2 === etf2.code) ||
                           (c.etf1 === etf2.code && c.etf2 === etf1.code)
                    )?.correlation || (etf1.code === etf2.code ? 1 : 0);
                    
                    const isHighCorrelation = correlation > 0.8 && etf1.code !== etf2.code;
                    
                    return (
                      <TableCell 
                        key={etf2.code} 
                        align="center"
                        sx={{
                          backgroundColor: isHighCorrelation ? 'error.light' : 
                                         etf1.code === etf2.code ? 'grey.200' : 
                                         'inherit',
                          color: isHighCorrelation ? 'error.contrastText' : 'inherit',
                        }}
                      >
                        <Typography variant="caption" fontWeight={600}>
                          {correlation.toFixed(2)}
                        </Typography>
                      </TableCell>
                    );
                  })}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        
        <Box mt={2}>
          <Typography variant="caption" color="text.secondary">
            注：红色标记表示相关性 &gt; 0.8，不包含核心标的(510300)
          </Typography>
        </Box>
      </Box>
    );
  };

  const renderQualificationDetail = () => {
    if (!qualificationDetails) return null;
    
    // Build failure message
    const failureReasons: string[] = [];
    if (!qualificationDetails.bufferPass) {
      failureReasons.push(`缓冲差 ${qualificationDetails.bufferValue.toFixed(1)}% < ${qualificationDetails.bufferThreshold}%`);
    }
    if (!qualificationDetails.minHoldingPass) {
      failureReasons.push(`持有期剩余 ${qualificationDetails.minHoldingDaysRemaining} 天`);
    }
    if (!qualificationDetails.correlationPass) {
      failureReasons.push(`相关性 ${qualificationDetails.correlationValue.toFixed(2)} > ${qualificationDetails.correlationThreshold}`);
    }
    if (!qualificationDetails.legLimitPass) {
      failureReasons.push(`腿数 ${qualificationDetails.currentLegCount} > ${qualificationDetails.maxLegCount}`);
    }
    
    return (
      <Stack spacing={2}>
        {/* Overall Status with detailed failure message */}
        <Box>
          <Box display="flex" alignItems="center" gap={1}>
            {qualificationDetails.overallPass ? (
              <CheckIcon sx={{ color: 'success.main', fontSize: 24 }} />
            ) : (
              <CancelIcon sx={{ color: 'error.main', fontSize: 24 }} />
            )}
            <Typography variant="subtitle1" fontWeight={600}>
              资格总览：{qualificationDetails.overallPass ? '通过' : '不通过'}
            </Typography>
          </Box>
          {!qualificationDetails.overallPass && failureReasons.length > 0 && (
            <Typography variant="caption" color="error.main" sx={{ ml: 4 }}>
              （未满足：{failureReasons.join('，')}）
            </Typography>
          )}
        </Box>
        
        <Divider />
        
        {/* Detail Items */}
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            {qualificationDetails.bufferPass ? (
              <CheckIcon sx={{ color: 'success.main', fontSize: 18 }} />
            ) : (
              <CancelIcon sx={{ color: 'error.main', fontSize: 18 }} />
            )}
            <Typography variant="body2">缓冲差</Typography>
          </Box>
          <Typography variant="body2" color={qualificationDetails.bufferPass ? 'success.main' : 'error.main'} fontWeight={600}>
            {qualificationDetails.bufferValue.toFixed(1)}% {qualificationDetails.bufferPass ? '≥' : '<'} {qualificationDetails.bufferThreshold}%
          </Typography>
        </Box>
        
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            {qualificationDetails.minHoldingPass ? (
              <CheckIcon sx={{ color: 'success.main', fontSize: 18 }} />
            ) : (
              <CancelIcon sx={{ color: 'error.main', fontSize: 18 }} />
            )}
            <Typography variant="body2">最短持有期</Typography>
          </Box>
          <Typography variant="body2" color={qualificationDetails.minHoldingPass ? 'success.main' : 'error.main'} fontWeight={600}>
            {qualificationDetails.minHoldingDaysRemaining === 0 ? '已满足' : `剩余 ${qualificationDetails.minHoldingDaysRemaining} 天`}
          </Typography>
        </Box>
        
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            {qualificationDetails.correlationPass ? (
              <CheckIcon sx={{ color: 'success.main', fontSize: 18 }} />
            ) : (
              <CancelIcon sx={{ color: 'error.main', fontSize: 18 }} />
            )}
            <Typography variant="body2">相关性限制</Typography>
          </Box>
          <Typography variant="body2" color={qualificationDetails.correlationPass ? 'success.main' : 'error.main'} fontWeight={600}>
            ρ = {qualificationDetails.correlationValue.toFixed(2)} {qualificationDetails.correlationPass ? '≤' : '>'} {qualificationDetails.correlationThreshold}
          </Typography>
        </Box>
        
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box display="flex" alignItems="center" gap={1}>
            {qualificationDetails.legLimitPass ? (
              <CheckIcon sx={{ color: 'success.main', fontSize: 18 }} />
            ) : (
              <CancelIcon sx={{ color: 'error.main', fontSize: 18 }} />
            )}
            <Typography variant="body2">腿数限制</Typography>
          </Box>
          <Typography variant="body2" color={qualificationDetails.legLimitPass ? 'success.main' : 'error.main'} fontWeight={600}>
            {qualificationDetails.currentLegCount} / {qualificationDetails.maxLegCount} 腿
          </Typography>
        </Box>
      </Stack>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Satellite模块
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<RotateIcon />}
            onClick={() => rotationMutation.mutate()}
            disabled={!isMonthEnd || !qualificationDetails?.overallPass || rotationMutation.isPending}
          >
            {!qualificationDetails?.overallPass ? '资格不合格' :
             isMonthEnd ? '生成换仓单' : 
             `下次轮动: ${format(endOfMonth(today), 'MM月dd日')}`}
          </Button>
          <Tooltip title="刷新">
            <IconButton onClick={() => refetchRankings()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Enhanced Momentum Rankings Table */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" fontWeight={600}>
                  动量排行（卫星候选池）
                </Typography>
                
                {/* Filters */}
                <Box display="flex" gap={2}>
                  <FormControl size="small" sx={{ minWidth: 150 }}>
                    <Select
                      value={filterOptions.growth}
                      onChange={(e) => setFilterOptions(prev => ({ ...prev, growth: e.target.value }))}
                      displayEmpty
                      startAdornment={<FilterIcon sx={{ mr: 1, fontSize: 18 }} />}
                    >
                      <MenuItem value="none">全部成长线</MenuItem>
                      <MenuItem value="516010">游戏动漫 (516010)</MenuItem>
                      <MenuItem value="159869">游戏动漫 (159869)</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl size="small" sx={{ minWidth: 180 }}>
                    <Select
                      value={filterOptions.newEnergy}
                      onChange={(e) => setFilterOptions(prev => ({ ...prev, newEnergy: e.target.value }))}
                      displayEmpty
                      startAdornment={<FilterIcon sx={{ mr: 1, fontSize: 18 }} />}
                    >
                      <MenuItem value="none">全部电新链</MenuItem>
                      <MenuItem value="516160">新能源 (516160)</MenuItem>
                      <MenuItem value="515790">光伏 (515790)</MenuItem>
                      <MenuItem value="515030">新能源车 (515030)</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              </Box>

              {rankingsLoading ? (
                <Box display="flex" justifyContent="center" py={3}>
                  <CircularProgress />
                </Box>
              ) : enhancedMomentumData && enhancedMomentumData.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>排名</TableCell>
                        <TableCell>代码</TableCell>
                        <TableCell>名称</TableCell>
                        <TableCell align="right">60日涨幅</TableCell>
                        <TableCell align="right">120日涨幅</TableCell>
                        <TableCell align="right">评分</TableCell>
                        <TableCell align="right">
                          <Tooltip title="日均成交额">
                            <Box display="flex" alignItems="center" justifyContent="flex-end">
                              成交额
                              <InfoIcon sx={{ fontSize: 14, ml: 0.5 }} />
                            </Box>
                          </Tooltip>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="与Top1的相关系数">
                            <Box display="flex" alignItems="center" justifyContent="flex-end">
                              ρ(Top1)
                              <InfoIcon sx={{ fontSize: 14, ml: 0.5 }} />
                            </Box>
                          </Tooltip>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="新评分与当前持仓评分之差">
                            <Box display="flex" alignItems="center" justifyContent="flex-end">
                              缓冲差
                              <InfoIcon sx={{ fontSize: 14, ml: 0.5 }} />
                            </Box>
                          </Tooltip>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="最短持有期剩余天数">
                            <Box display="flex" alignItems="center" justifyContent="flex-end">
                              剩余持有
                              <InfoIcon sx={{ fontSize: 14, ml: 0.5 }} />
                            </Box>
                          </Tooltip>
                        </TableCell>
                        <TableCell>状态</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {enhancedMomentumData.map((etf, index) => (
                        <TableRow 
                          key={etf.code}
                          sx={{ 
                            backgroundColor: etf.isHolding ? 'warning.light' :
                                           index === 0 ? 'primary.light' : 'inherit',
                            '& td': {
                              color: index === 0 || etf.isHolding ? 'primary.contrastText' : 'inherit',
                            }
                          }}
                        >
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>
                              #{index + 1}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" fontWeight={600}>
                              {etf.code}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {etf.name}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography 
                              variant="body2" 
                              color={etf.r60 > 0 ? 'success.main' : 'error.main'}
                            >
                              {etf.r60.toFixed(1)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography 
                              variant="body2"
                              color={etf.r120 > 0 ? 'success.main' : 'error.main'}
                            >
                              {etf.r120.toFixed(1)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" fontWeight={600}>
                              {etf.score.toFixed(2)}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">
                              {etf.volume?.toFixed(1) || '-'}亿
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography 
                              variant="body2"
                              color={etf.correlationWithTop1 > 0.8 ? 'error.main' : 'text.primary'}
                              fontWeight={etf.correlationWithTop1 > 0.8 ? 600 : 400}
                            >
                              {etf.correlationWithTop1.toFixed(2)}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography 
                              variant="body2"
                              color={etf.bufferDiff >= 3 ? 'success.main' : etf.bufferDiff < 0 ? 'error.main' : 'text.primary'}
                            >
                              {etf.bufferDiff > 0 ? '+' : ''}{etf.bufferDiff.toFixed(1)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography 
                              variant="body2"
                              color={etf.minHoldingDaysRemaining > 0 ? 'warning.main' : 'success.main'}
                            >
                              {etf.minHoldingDaysRemaining > 0 ? `${etf.minHoldingDaysRemaining}天` : '-'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            {etf.isHolding ? (
                              <Chip label="持有中" size="small" color="warning" />
                            ) : index === 0 && qualificationDetails?.overallPass ? (
                              <Chip label="候选" size="small" color="primary" />
                            ) : (
                              <Chip label="观察" size="small" variant="outlined" />
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info">暂无动量数据</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Right Column */}
        <Grid item xs={12} lg={4}>
          <Grid container spacing={3}>
            {/* Enhanced Qualification Status */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    资格状态（统一判定）
                  </Typography>
                  
                  {renderQualificationDetail()}
                </CardContent>
              </Card>
            </Grid>

            {/* Correlation Heatmap - Satellite Only */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    与Top1的相关性
                  </Typography>
                  
                  {correlationLoading ? (
                    <Box display="flex" justifyContent="center" py={3}>
                      <CircularProgress />
                    </Box>
                  ) : correlationData ? (
                    renderCorrelationHeatmap()
                  ) : (
                    <Alert severity="info">选择ETF以查看相关性数据</Alert>
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

export default SatelliteModuleEnhanced;