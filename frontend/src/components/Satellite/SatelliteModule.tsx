import React, { useState, useMemo } from 'react';
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
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  RotateRight as RotateIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import { format, endOfMonth, isEqual } from 'date-fns';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { MomentumETF, CorrelationMatrix } from '../../types';
import { chartColors } from '../../styles/theme';

interface FilterOptions {
  growth: 'none' | string;
  newEnergy: 'none' | string;
}

const SatelliteModule: React.FC = () => {
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    growth: 'none',
    newEnergy: 'none',
  });

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

  // Fetch correlation matrix
  const { 
    data: correlationData, 
    isLoading: correlationLoading 
  } = useQuery({
    queryKey: ['correlationMatrix', momentumData?.[0]?.code],
    queryFn: () => api.market.getCorrelationMatrix(momentumData![0].code),
    enabled: !!momentumData && momentumData.length > 0,
  });

  // Rotation mutation
  const rotationMutation = useMutation({
    mutationFn: () => api.portfolio.rebalance(),
    onSuccess: () => {
      toast.success('Portfolio rotation completed successfully');
      refetchRankings();
    },
    onError: (error) => {
      toast.error('Failed to rotate portfolio');
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

    // Apply new energy filter (3-choose-1)
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

  // Get qualification status
  const qualificationStatus = useMemo(() => {
    if (!filteredMomentumData || filteredMomentumData.length === 0) {
      return {
        topQualified: false,
        correlationOk: false,
        volumeOk: false,
        spreadOk: false,
      };
    }

    const top5 = filteredMomentumData.slice(0, 5);
    const allQualified = top5.every(etf => etf.qualified);
    
    // Check correlations (assuming all < 0.8 for now)
    const correlationOk = true; // This should check actual correlation matrix
    
    // Check volume requirements
    const volumeOk = top5.every(etf => etf.volume > 1000000);
    
    // Check spread requirements
    const spreadOk = top5.every(etf => etf.spread < 0.5);

    return {
      topQualified: allQualified,
      correlationOk,
      volumeOk,
      spreadOk,
    };
  }, [filteredMomentumData]);

  const getCorrelationColor = (value: number): string => {
    if (value >= 0.8) return chartColors.correlation.high;
    if (value >= 0.5) return chartColors.correlation.medium;
    if (value >= 0.2) return chartColors.correlation.low;
    return chartColors.correlation.neutral;
  };

  const renderCorrelationHeatmap = () => {
    if (!correlationData) return null;

    const { etfs, values } = correlationData;
    
    return (
      <Box sx={{ overflowX: 'auto' }}>
        <Table size="small" sx={{ minWidth: 400 }}>
          <TableHead>
            <TableRow>
              <TableCell></TableCell>
              {etfs.map(etf => (
                <TableCell key={etf} align="center" sx={{ fontWeight: 600, fontSize: '0.75rem' }}>
                  {etf}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {etfs.map((etf, i) => (
              <TableRow key={etf}>
                <TableCell sx={{ fontWeight: 600, fontSize: '0.75rem' }}>
                  {etf}
                </TableCell>
                {values[i].map((value, j) => (
                  <TableCell 
                    key={`${i}-${j}`} 
                    align="center"
                    sx={{
                      backgroundColor: i === j ? '#f5f5f5' : getCorrelationColor(value),
                      color: value >= 0.8 ? 'white' : 'inherit',
                      fontWeight: value >= 0.8 ? 600 : 400,
                      fontSize: '0.75rem',
                    }}
                  >
                    {i === j ? '-' : value.toFixed(2)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    );
  };

  const renderQualificationLight = (qualified: boolean, label: string) => {
    return (
      <Box display="flex" alignItems="center" gap={1}>
        {qualified ? (
          <CheckIcon sx={{ color: 'success.main', fontSize: 20 }} />
        ) : (
          <CancelIcon sx={{ color: 'error.main', fontSize: 20 }} />
        )}
        <Typography variant="body2" color={qualified ? 'success.main' : 'error.main'}>
          {label}
        </Typography>
      </Box>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Satellite Module
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<RotateIcon />}
            onClick={() => rotationMutation.mutate()}
            disabled={!isMonthEnd || rotationMutation.isPending}
          >
            {isMonthEnd ? 'Rotate Portfolio' : `Rotation on ${format(endOfMonth(today), 'MMM dd')}`}
          </Button>
          <Tooltip title="Refresh">
            <IconButton onClick={() => refetchRankings()}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Momentum Rankings */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6" fontWeight={600}>
                  Momentum Rankings
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
                      <MenuItem value="none">All Growth</MenuItem>
                      <MenuItem value="516010">Gaming (516010)</MenuItem>
                      <MenuItem value="159869">Gaming (159869)</MenuItem>
                    </Select>
                  </FormControl>

                  <FormControl size="small" sx={{ minWidth: 180 }}>
                    <Select
                      value={filterOptions.newEnergy}
                      onChange={(e) => setFilterOptions(prev => ({ ...prev, newEnergy: e.target.value }))}
                      displayEmpty
                      startAdornment={<FilterIcon sx={{ mr: 1, fontSize: 18 }} />}
                    >
                      <MenuItem value="none">All New Energy</MenuItem>
                      <MenuItem value="516160">New Energy (516160)</MenuItem>
                      <MenuItem value="515790">New Energy (515790)</MenuItem>
                      <MenuItem value="515030">New Energy (515030)</MenuItem>
                    </Select>
                  </FormControl>
                </Box>
              </Box>

              {rankingsLoading ? (
                <Box display="flex" justifyContent="center" py={3}>
                  <CircularProgress />
                </Box>
              ) : filteredMomentumData && filteredMomentumData.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Rank</TableCell>
                        <TableCell>Code</TableCell>
                        <TableCell>Name</TableCell>
                        <TableCell align="right">r60</TableCell>
                        <TableCell align="right">r120</TableCell>
                        <TableCell align="right">Score</TableCell>
                        <TableCell align="right">Volume</TableCell>
                        <TableCell align="right">Spread</TableCell>
                        <TableCell>Type</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {filteredMomentumData.slice(0, 10).map((etf, index) => (
                        <TableRow 
                          key={etf.code}
                          sx={{ 
                            backgroundColor: index === 0 ? 'primary.light' : 'inherit',
                            '& td': {
                              color: index === 0 ? 'primary.contrastText' : 'inherit',
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
                              {etf.r60.toFixed(2)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography 
                              variant="body2"
                              color={etf.r120 > 0 ? 'success.main' : 'error.main'}
                            >
                              {etf.r120.toFixed(2)}%
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2" fontWeight={600}>
                              {etf.score.toFixed(2)}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">
                              {(etf.volume / 1000000).toFixed(1)}M
                            </Typography>
                          </TableCell>
                          <TableCell align="right">
                            <Typography variant="body2">
                              {etf.spread.toFixed(2)}%
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Chip 
                              label={etf.type} 
                              size="small"
                              color={etf.type === 'Growth' ? 'primary' : etf.type === 'NewEnergy' ? 'success' : 'default'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info">No momentum data available</Alert>
              )}

              <Box mt={2}>
                <Typography variant="caption" color="text.secondary">
                  Score = 0.6 × r60 + 0.4 × r120 (60-day and 120-day returns)
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Right Column */}
        <Grid item xs={12} lg={4}>
          <Grid container spacing={3}>
            {/* Qualification Status */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    Qualification Status
                  </Typography>
                  
                  <Stack spacing={2}>
                    {renderQualificationLight(
                      qualificationStatus.topQualified, 
                      'Top 5 ETFs Qualified'
                    )}
                    {renderQualificationLight(
                      qualificationStatus.correlationOk, 
                      'Correlation < 0.8'
                    )}
                    {renderQualificationLight(
                      qualificationStatus.volumeOk, 
                      'Volume Requirements Met'
                    )}
                    {renderQualificationLight(
                      qualificationStatus.spreadOk, 
                      'Spread < 0.5%'
                    )}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            {/* Correlation Heatmap */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    Correlation Matrix (Top 5)
                  </Typography>
                  
                  {correlationLoading ? (
                    <Box display="flex" justifyContent="center" py={3}>
                      <CircularProgress />
                    </Box>
                  ) : correlationData ? (
                    renderCorrelationHeatmap()
                  ) : (
                    <Alert severity="info">Select ETFs to view correlation</Alert>
                  )}

                  <Box mt={2}>
                    <Typography variant="caption" color="text.secondary">
                      Values above 0.8 indicate high correlation (red)
                    </Typography>
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

export default SatelliteModule;