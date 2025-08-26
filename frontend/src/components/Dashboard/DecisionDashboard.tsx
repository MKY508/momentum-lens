import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Button,
  Grid,
  FormControl,
  Select,
  MenuItem,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
  Snackbar,
  Divider,
  Stack,
  Paper,
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format } from 'date-fns';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { Decision, MarketIndicator, ParameterPreset } from '../../types';
import { indicatorColors } from '../../styles/theme';
import CoreSnapshot from './CoreSnapshot';
import DataSourceControl from '../Common/DataSourceControl';

const PARAMETER_PRESETS: ParameterPreset[] = [
  {
    name: '进攻',
    stopLoss: 10,
    buffer: 2,
    minHolding: 14,
    bandwidth: 5,
    correlationThreshold: 0.8,
  },
  {
    name: '均衡',
    stopLoss: 12,
    buffer: 3,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
  {
    name: '保守',
    stopLoss: 15,
    buffer: 4,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
];

// Helper function to get ETF status message
const getETFStatusMessage = (status: string): string => {
  switch (status) {
    case 'SUSPENDED':
      return 'ETF已停牌，无法交易';
    case 'MERGED':
      return 'ETF已合并，请选择新标的';
    case 'DELISTED':
      return 'ETF已退市';
    case 'NO_DATA':
      return '无法获取数据，请稍后重试';
    default:
      return '状态异常';
  }
};

// Helper function to format numbers with thousand separators
const formatNumber = (num: number | undefined): string => {
  if (num === undefined) return 'N/A';
  return num.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
};

const DecisionDashboard: React.FC = () => {
  const [selectedPreset, setSelectedPreset] = useState<string>('均衡');
  const [showCopiedAlert, setShowCopiedAlert] = useState(false);

  // Fetch market indicators
  const { data: indicators, isLoading: indicatorsLoading, refetch: refetchIndicators } = useQuery({
    queryKey: ['marketIndicators'],
    queryFn: api.market.getIndicators,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch current decision
  const { data: decision, isLoading: decisionLoading, refetch: refetchDecision } = useQuery({
    queryKey: ['currentDecision'],
    queryFn: api.decisions.getCurrent,
    refetchInterval: 60000, // Refresh every minute
  });

  // Calculate new decision mutation
  const calculateDecisionMutation = useMutation({
    mutationFn: (preset: ParameterPreset) => api.decisions.calculate(preset),
    onSuccess: (newDecision) => {
      toast.success('新决策计算成功');
      refetchDecision();
    },
    onError: (error) => {
      toast.error('决策计算失败');
      console.error('Decision calculation error:', error);
    },
  });

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    const presetConfig = PARAMETER_PRESETS.find(p => p.name === preset);
    if (presetConfig) {
      calculateDecisionMutation.mutate(presetConfig);
    }
  };

  const handleCopyOrder = useCallback(() => {
    if (!decision) return;

    const orderText = `
ETF交易订单
================
时间窗口:
10:30 ${decision.firstLeg.code} ${decision.firstLeg.name} ${decision.weights.trial}% 限价 = IOPV×[0.999,1.001]
14:00 ${decision.secondLeg.code} ${decision.secondLeg.name} ${decision.weights.trial}% 限价 = IOPV×[0.999,1.001]

第一腿: ${decision.firstLeg.code} ${decision.firstLeg.name}
动量评分: ${decision.firstLeg.score.toFixed(1)}
权重: ${decision.weights.trial}% (试仓) / ${decision.weights.full}% (全仓)

第二腿: ${decision.secondLeg.code} ${decision.secondLeg.name}
动量评分: ${decision.secondLeg.score.toFixed(1)}
权重: ${decision.weights.trial}% (试仓) / ${decision.weights.full}% (全仓)

IOPV区间: [${decision.iopvBands.lower}, ${decision.iopvBands.upper}]
时间戳: ${format(new Date(decision.timestamp), 'yyyy-MM-dd HH:mm:ss')}
    `.trim();

    navigator.clipboard.writeText(orderText);
    setShowCopiedAlert(true);
    toast.success('订单已复制到剪贴板');
  }, [decision]);

  const handleExportCSV = useCallback(async () => {
    try {
      const blob = await api.trading.exportTrades('csv');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `decision_${format(new Date(), 'yyyyMMdd_HHmmss')}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('CSV导出成功');
    } catch (error) {
      toast.error('CSV导出失败');
      console.error('Export error:', error);
    }
  }, []);

  const handleExportPDF = useCallback(async () => {
    try {
      const blob = await api.trading.exportTrades('pdf');
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `decision_${format(new Date(), 'yyyyMMdd_HHmmss')}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success('PDF导出成功');
    } catch (error) {
      toast.error('PDF导出失败');
      console.error('Export error:', error);
    }
  }, []);

  const renderIndicatorChip = (
    label: string,
    status: 'positive' | 'negative' | 'neutral',
    value?: string | number
  ) => {
    const color = status === 'positive' ? 'success' : status === 'negative' ? 'error' : 'warning';
    const bgColor = status === 'positive' 
      ? indicatorColors.qualified 
      : status === 'negative' 
      ? indicatorColors.notQualified 
      : indicatorColors.chopChoppy;

    return (
      <Chip
        label={value ? `${label}: ${value}` : label}
        color={color}
        size="small"
        sx={{
          fontWeight: 600,
          backgroundColor: bgColor,
          color: 'white',
          '& .MuiChip-label': {
            px: 2,
          },
        }}
      />
    );
  };

  const renderQualificationLight = (qualified: boolean, label: string) => {
    return (
      <Box display="flex" alignItems="center" gap={1}>
        {qualified ? (
          <CheckIcon sx={{ color: indicatorColors.qualified, fontSize: 20 }} />
        ) : (
          <CancelIcon sx={{ color: indicatorColors.notQualified, fontSize: 20 }} />
        )}
        <Typography variant="body2" color={qualified ? 'success.main' : 'error.main'}>
          {label}
        </Typography>
      </Box>
    );
  };

  const isLoading = indicatorsLoading || decisionLoading;

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          决策台
        </Typography>
        <Box display="flex" gap={2} alignItems="center">
          <DataSourceControl 
            embedded={true} 
            onDataUpdate={() => {
              refetchDecision();
              refetchIndicators();
            }}
          />
          <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <Select
              value={selectedPreset}
              onChange={(e) => handlePresetChange(e.target.value)}
              displayEmpty
            >
              {PARAMETER_PRESETS.map((preset) => (
                <MenuItem key={preset.name} value={preset.name}>
                  {preset.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Tooltip title="刷新">
            <IconButton 
              onClick={() => refetchDecision()} 
              disabled={isLoading}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Environment Indicators */}
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
        <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
          <Typography variant="subtitle1" fontWeight={600}>
            市场环境：
          </Typography>
          {indicatorsLoading ? (
            <CircularProgress size={20} />
          ) : indicators ? (
            <>
              <Tooltip title={`收盘 ${formatNumber(indicators.yearline.value)} / MA200 ${formatNumber(indicators.yearline.ma200)}`}>
                <Box>
                  {renderIndicatorChip(
                    '年线',
                    indicators.yearline.status === 'ABOVE' ? 'positive' : 'negative',
                    `${indicators.yearline.status === 'ABOVE' ? '在上' : '在下'} (${indicators.yearline.deviation ? `${indicators.yearline.deviation > 0 ? '+' : ''}${indicators.yearline.deviation.toFixed(1)}%` : 'N/A'})`
                  )}
                </Box>
              </Tooltip>
              {renderIndicatorChip(
                'ATR20/价',
                indicators.atr.status === 'LOW' ? 'positive' : indicators.atr.status === 'HIGH' ? 'negative' : 'neutral',
                `${indicators.atr.value.toFixed(1)}%`
              )}
              <Tooltip title={`3选2准则: ${indicators.chop.inBandDays || 0}/30天带内 | ATR/价${indicators.atr.value.toFixed(1)}% | CHOP=${indicators.chop.status === 'CHOPPY' ? 'ON' : 'OFF'}`}>
                <Box>
                  {renderIndicatorChip(
                    'CHOP',
                    indicators.chop.status === 'TRENDING' ? 'positive' : 'neutral',
                    `带内 ${indicators.chop.inBandDays || 0}/30 | CHOP=${indicators.chop.status === 'CHOPPY' ? 'ON' : 'OFF'}`
                  )}
                </Box>
              </Tooltip>
              {indicators.chop.status === 'CHOPPY' && (
                <Tooltip title="震荡市条件：带内天数>50% ✓ ATR/价<2.5% ✓">
                  <Chip
                    label="震荡: ON"
                    color="warning"
                    size="small"
                    icon={<InfoIcon />}
                    sx={{
                      fontWeight: 600,
                      backgroundColor: indicatorColors.chopChoppy,
                      color: 'white',
                    }}
                  />
                </Tooltip>
              )}
            </>
          ) : null}
        </Box>
      </Paper>

      {/* Main Decision Card */}
      {isLoading ? (
        <Box display="flex" justifyContent="center" py={5}>
          <CircularProgress />
        </Box>
      ) : decision ? (
        <Card elevation={2}>
          <CardContent>
            <Grid container spacing={3}>
              {/* Left Column - ETF Selection */}
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  选中ETF
                </Typography>
                
                <Box mb={3}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    第一腿
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="h6">
                          {decision.firstLeg.code}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {decision.firstLeg.name}
                        </Typography>
                        {decision.firstLeg.status && decision.firstLeg.status !== 'NORMAL' && (
                          <Alert severity="error" sx={{ mt: 1 }}>
                            {decision.firstLeg.statusMessage || getETFStatusMessage(decision.firstLeg.status)}
                            <Button disabled sx={{ ml: 1 }}>不可下单</Button>
                          </Alert>
                        )}
                      </Box>
                      <Box display="flex" flexDirection="column" alignItems="flex-end" gap={1}>
                        <Chip 
                          label={`评分: ${decision.firstLeg.score.toFixed(1)}`}
                          color="primary"
                          size="small"
                        />
                        {decision.firstLeg.status && decision.firstLeg.status !== 'NORMAL' && (
                          <Chip 
                            label={decision.firstLeg.status}
                            color="error"
                            size="small"
                          />
                        )}
                      </Box>
                    </Box>
                  </Paper>
                </Box>

                <Box mb={3}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    第二腿
                  </Typography>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Box>
                        <Typography variant="h6">
                          {decision.secondLeg.code}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {decision.secondLeg.name}
                        </Typography>
                        {decision.secondLeg.status && decision.secondLeg.status !== 'NORMAL' && (
                          <Alert severity="error" sx={{ mt: 1 }}>
                            {decision.secondLeg.statusMessage || getETFStatusMessage(decision.secondLeg.status)}
                            <Button disabled sx={{ ml: 1 }}>不可下单</Button>
                          </Alert>
                        )}
                      </Box>
                      <Box display="flex" flexDirection="column" alignItems="flex-end" gap={1}>
                        <Chip 
                          label={`评分: ${decision.secondLeg.score.toFixed(1)}`}
                          color="primary"
                          size="small"
                        />
                        {decision.secondLeg.status && decision.secondLeg.status !== 'NORMAL' && (
                          <Chip 
                            label={decision.secondLeg.status}
                            color="error"
                            size="small"
                          />
                        )}
                      </Box>
                    </Box>
                  </Paper>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    建议权重
                  </Typography>
                  <Stack spacing={1}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2">试仓：</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {decision.weights.trial}%
                      </Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2">全仓：</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {decision.weights.full}%
                      </Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2">IOPV区间：</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        [{decision.iopvBands.lower}, {decision.iopvBands.upper}]
                      </Typography>
                    </Box>
                  </Stack>
                </Box>
              </Grid>

              <Divider orientation="vertical" flexItem sx={{ mx: 2 }} />

              {/* Right Column - Qualifications */}
              <Grid item xs={12} md={5}>
                {/* Core 快照 - 放在QDII状态上方 */}
                <Box mb={3}>
                  <CoreSnapshot 
                    yearline={indicators?.yearline}
                    qdiiStatus={decision.qdiiStatus}
                  />
                </Box>
                
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  资格状态
                </Typography>

                <Stack spacing={2} mb={3}>
                  {renderQualificationLight(
                    decision.qualifications.buffer, 
                    decision.qualifications.bufferValue && decision.qualifications.bufferThreshold
                      ? `Buffer: ${decision.qualifications.bufferValue > 0 ? '+' : ''}${decision.qualifications.bufferValue.toFixed(1)}% ≥ ${decision.qualifications.bufferThreshold.toFixed(0)}% ✓`
                      : '缓冲区要求'
                  )}
                  {renderQualificationLight(
                    decision.qualifications.minHolding, 
                    decision.qualifications.minHoldingDays && decision.qualifications.minHoldingRequired
                      ? `Min holding: 已满 ${decision.qualifications.minHoldingDays}/${decision.qualifications.minHoldingRequired} 天 ✓`
                      : '最短持有期'
                  )}
                  {renderQualificationLight(
                    decision.qualifications.correlation, 
                    decision.qualifications.correlationValue && decision.qualifications.correlationThreshold
                      ? `Correlation: ρ(Top1,候选)=${decision.qualifications.correlationValue.toFixed(2)} ≤ ${decision.qualifications.correlationThreshold.toFixed(1)} ✓`
                      : '相关系数 ≤ 0.8'
                  )}
                  {renderQualificationLight(
                    decision.qualifications.legLimit, 
                    decision.qualifications.currentLegs !== undefined && decision.qualifications.maxLegs
                      ? `Leg limit: 年线上，允许 ${decision.qualifications.maxLegs} 条 ✓`
                      : '腿数限制要求'
                  )}
                </Stack>

                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    QDII状态
                  </Typography>
                  <Paper 
                    variant="outlined" 
                    sx={{ 
                      p: 2,
                      backgroundColor: decision.qdiiStatus.premium <= 2 
                        ? 'rgba(76, 175, 80, 0.1)' 
                        : decision.qdiiStatus.premium >= 3
                        ? 'rgba(244, 67, 54, 0.1)'
                        : 'rgba(255, 152, 0, 0.1)'
                    }}
                  >
                    <Stack spacing={1}>
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="body2" fontWeight={600}>
                          标普500 溢价 {decision.qdiiStatus.premium.toFixed(1)}%
                        </Typography>
                        <Chip
                          label={
                            decision.qdiiStatus.premium <= 2 
                              ? `(≤2% 可买)` 
                              : decision.qdiiStatus.premium >= 3
                              ? `(≥3% 暂停，停放 511990)`
                              : '(观察中)'
                          }
                          color={
                            decision.qdiiStatus.premium <= 2 
                              ? 'success' 
                              : decision.qdiiStatus.premium >= 3
                              ? 'error'
                              : 'warning'
                          }
                          size="small"
                        />
                      </Box>
                      {decision.qdiiStatus.premium >= 3 && (
                        <Alert severity="warning" sx={{ py: 0.5 }}>
                          <Typography variant="caption">
                            {decision.qdiiStatus.premium.toFixed(1)}% (≥3% 暂停，停放 511990)
                          </Typography>
                        </Alert>
                      )}
                      <Typography variant="caption" color="text.secondary">
                        买入阈值: ≤2% | 暂停阈值: ≥3%
                      </Typography>
                    </Stack>
                  </Paper>
                </Box>

                <Box mt={3}>
                  <Typography variant="caption" color="text.secondary">
                    更新时间: {format(new Date(decision.timestamp), 'yyyy-MM-dd HH:mm:ss')}
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {/* Action Buttons */}
            <Divider sx={{ my: 3 }} />
            <Box display="flex" gap={2} justifyContent="flex-end">
              <Button
                variant="contained"
                startIcon={<CopyIcon />}
                onClick={handleCopyOrder}
              >
                复制订单
              </Button>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportCSV}
              >
                导出CSV
              </Button>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportPDF}
              >
                导出PDF
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info">
          暂无决策数据，请点击刷新按钮生成新决策。
        </Alert>
      )}

      {/* Copied Alert */}
      <Snackbar
        open={showCopiedAlert}
        autoHideDuration={3000}
        onClose={() => setShowCopiedAlert(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setShowCopiedAlert(false)} severity="success">
          订单已复制到剪贴板！
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DecisionDashboard;