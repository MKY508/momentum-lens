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

const PARAMETER_PRESETS: ParameterPreset[] = [
  {
    name: 'Aggressive',
    stopLoss: 10,
    buffer: 2,
    minHolding: 14,
    bandwidth: 5,
    correlationThreshold: 0.8,
  },
  {
    name: 'Balanced',
    stopLoss: 12,
    buffer: 3,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
  {
    name: 'Conservative',
    stopLoss: 15,
    buffer: 4,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
];

const DecisionDashboard: React.FC = () => {
  const [selectedPreset, setSelectedPreset] = useState<string>('Balanced');
  const [showCopiedAlert, setShowCopiedAlert] = useState(false);

  // Fetch market indicators
  const { data: indicators, isLoading: indicatorsLoading } = useQuery({
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
      toast.success('New decision calculated successfully');
      refetchDecision();
    },
    onError: (error) => {
      toast.error('Failed to calculate decision');
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
ETF Trading Order
================
First Leg: ${decision.firstLeg.code} ${decision.firstLeg.name}
Score: ${decision.firstLeg.score.toFixed(2)}
Weight: ${decision.weights.trial}% (Trial) / ${decision.weights.full}% (Full)

Second Leg: ${decision.secondLeg.code} ${decision.secondLeg.name}
Score: ${decision.secondLeg.score.toFixed(2)}
Weight: ${decision.weights.trial}% (Trial) / ${decision.weights.full}% (Full)

IOPV Bands: [${decision.iopvBands.lower}, ${decision.iopvBands.upper}]
Timestamp: ${format(new Date(decision.timestamp), 'yyyy-MM-dd HH:mm:ss')}
    `.trim();

    navigator.clipboard.writeText(orderText);
    setShowCopiedAlert(true);
    toast.success('Order copied to clipboard');
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
      toast.success('CSV exported successfully');
    } catch (error) {
      toast.error('Failed to export CSV');
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
      toast.success('PDF exported successfully');
    } catch (error) {
      toast.error('Failed to export PDF');
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
          Decision Dashboard
        </Typography>
        <Box display="flex" gap={2} alignItems="center">
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
          <Tooltip title="Refresh">
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
        <Box display="flex" gap={2} alignItems="center">
          <Typography variant="subtitle1" fontWeight={600}>
            Market Environment:
          </Typography>
          {indicatorsLoading ? (
            <CircularProgress size={20} />
          ) : indicators ? (
            <>
              {renderIndicatorChip(
                'Yearline',
                indicators.yearline.status === 'ABOVE' ? 'positive' : 'negative',
                indicators.yearline.status
              )}
              {renderIndicatorChip(
                'ATR',
                indicators.atr.status === 'LOW' ? 'positive' : indicators.atr.status === 'HIGH' ? 'negative' : 'neutral',
                indicators.atr.value.toFixed(2)
              )}
              {renderIndicatorChip(
                'CHOP',
                indicators.chop.status === 'TRENDING' ? 'positive' : 'neutral',
                indicators.chop.value.toFixed(2)
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
                  Selected ETFs
                </Typography>
                
                <Box mb={3}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    First Leg
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
                      </Box>
                      <Chip 
                        label={`Score: ${decision.firstLeg.score.toFixed(2)}`}
                        color="primary"
                        size="small"
                      />
                    </Box>
                  </Paper>
                </Box>

                <Box mb={3}>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Second Leg
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
                      </Box>
                      <Chip 
                        label={`Score: ${decision.secondLeg.score.toFixed(2)}`}
                        color="primary"
                        size="small"
                      />
                    </Box>
                  </Paper>
                </Box>

                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    Suggested Weights
                  </Typography>
                  <Stack spacing={1}>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2">Trial Position:</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {decision.weights.trial}%
                      </Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2">Full Position:</Typography>
                      <Typography variant="body2" fontWeight={600}>
                        {decision.weights.full}%
                      </Typography>
                    </Box>
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2">IOPV Bands:</Typography>
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
                <Typography variant="h6" gutterBottom fontWeight={600}>
                  Qualification Status
                </Typography>

                <Stack spacing={2} mb={3}>
                  {renderQualificationLight(decision.qualifications.buffer, 'Buffer Requirement')}
                  {renderQualificationLight(decision.qualifications.minHolding, 'Min Holding Period')}
                  {renderQualificationLight(decision.qualifications.correlation, 'Correlation ≤ 0.8')}
                  {renderQualificationLight(decision.qualifications.legLimit, 'Leg Limit')}
                </Stack>

                <Box>
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    QDII Status (513500)
                  </Typography>
                  <Paper 
                    variant="outlined" 
                    sx={{ 
                      p: 2,
                      backgroundColor: decision.qdiiStatus.status === 'OK' 
                        ? 'success.light' 
                        : decision.qdiiStatus.status === 'WARNING'
                        ? 'warning.light'
                        : 'error.light',
                      opacity: 0.1
                    }}
                  >
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="body2">
                        Premium: {decision.qdiiStatus.premium.toFixed(2)}%
                      </Typography>
                      <Chip
                        label={decision.qdiiStatus.status}
                        color={
                          decision.qdiiStatus.status === 'OK' 
                            ? 'success' 
                            : decision.qdiiStatus.status === 'WARNING'
                            ? 'warning'
                            : 'error'
                        }
                        size="small"
                      />
                    </Box>
                  </Paper>
                </Box>

                <Box mt={3}>
                  <Typography variant="caption" color="text.secondary">
                    Last Updated: {format(new Date(decision.timestamp), 'yyyy-MM-dd HH:mm:ss')}
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
                Copy Order
              </Button>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportCSV}
              >
                Export CSV
              </Button>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportPDF}
              >
                Export PDF
              </Button>
            </Box>
          </CardContent>
        </Card>
      ) : (
        <Alert severity="info">
          No decision available. Click refresh to generate a new decision.
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
          Order copied to clipboard!
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DecisionDashboard;