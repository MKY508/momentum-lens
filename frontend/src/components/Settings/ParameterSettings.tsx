import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Slider,
  FormControl,
  FormControlLabel,
  RadioGroup,
  Radio,
  Switch,
  Button,
  Divider,
  Alert,
  Chip,
  TextField,
  InputAdornment,
  Paper,
  Stack,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Save as SaveIcon,
  Restore as RestoreIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { Settings, ParameterPreset } from '../../types';

const PRESET_CONFIGS: Record<string, ParameterPreset> = {
  Aggressive: {
    name: 'Aggressive',
    stopLoss: 10,
    buffer: 2,
    minHolding: 14,
    bandwidth: 5,
    correlationThreshold: 0.8,
  },
  Balanced: {
    name: 'Balanced',
    stopLoss: 12,
    buffer: 3,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
  Conservative: {
    name: 'Conservative',
    stopLoss: 15,
    buffer: 4,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
};

const ETF_POOLS = {
  gaming: [
    { code: '516010', name: 'Gaming ETF A' },
    { code: '159869', name: 'Gaming ETF B' },
  ],
  newEnergy: [
    { code: '516160', name: 'New Energy ETF A' },
    { code: '515790', name: 'New Energy ETF B' },
    { code: '515030', name: 'New Energy ETF C' },
  ],
};

const ParameterSettings: React.FC = () => {
  const [selectedPreset, setSelectedPreset] = useState<string>('Balanced');
  const [customParams, setCustomParams] = useState<ParameterPreset>(PRESET_CONFIGS.Balanced);
  const [etfPool, setEtfPool] = useState({
    gaming: '516010',
    newEnergy: '516160',
  });
  const [notifications, setNotifications] = useState({
    alerts: true,
    trades: true,
    rebalancing: true,
  });
  const [displaySettings, setDisplaySettings] = useState({
    theme: 'light' as 'light' | 'dark',
    compactMode: false,
    showPremiums: true,
  });
  const [hasChanges, setHasChanges] = useState(false);

  // Fetch current settings
  const { data: settings, isLoading, refetch } = useQuery({
    queryKey: ['settings'],
    queryFn: api.config.getSettings,
    onSuccess: (data) => {
      if (data) {
        setSelectedPreset(data.preset.name);
        setCustomParams(data.preset);
        setEtfPool({
          gaming: data.etfPool.gaming,
          newEnergy: data.etfPool.newEnergy,
        });
        setNotifications(data.notifications);
        setDisplaySettings(data.display);
      }
    },
  });

  // Save settings mutation
  const saveSettingsMutation = useMutation({
    mutationFn: (newSettings: Partial<Settings>) => api.config.updateSettings(newSettings),
    onSuccess: () => {
      toast.success('Settings saved successfully');
      setHasChanges(false);
      refetch();
    },
    onError: (error) => {
      toast.error('Failed to save settings');
      console.error('Settings save error:', error);
    },
  });

  // Track changes
  useEffect(() => {
    if (settings) {
      const hasParamChanges = 
        JSON.stringify(customParams) !== JSON.stringify(settings.preset) ||
        selectedPreset !== settings.preset.name;
      
      const hasEtfChanges = 
        etfPool.gaming !== settings.etfPool.gaming ||
        etfPool.newEnergy !== settings.etfPool.newEnergy;
      
      const hasNotificationChanges = 
        JSON.stringify(notifications) !== JSON.stringify(settings.notifications);
      
      const hasDisplayChanges = 
        JSON.stringify(displaySettings) !== JSON.stringify(settings.display);

      setHasChanges(hasParamChanges || hasEtfChanges || hasNotificationChanges || hasDisplayChanges);
    }
  }, [customParams, selectedPreset, etfPool, notifications, displaySettings, settings]);

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    if (preset !== 'Custom' && PRESET_CONFIGS[preset]) {
      setCustomParams(PRESET_CONFIGS[preset]);
    }
  };

  const handleParameterChange = (param: keyof ParameterPreset, value: number) => {
    setCustomParams(prev => ({ ...prev, [param]: value }));
    setSelectedPreset('Custom');
  };

  const handleSave = () => {
    const newSettings: Partial<Settings> = {
      preset: { ...customParams, name: selectedPreset as any },
      etfPool: {
        ...etfPool,
        excludedETFs: settings?.etfPool.excludedETFs || [],
      },
      notifications,
      display: displaySettings,
    };
    
    saveSettingsMutation.mutate(newSettings);
  };

  const handleReset = () => {
    if (settings) {
      setSelectedPreset(settings.preset.name);
      setCustomParams(settings.preset);
      setEtfPool({
        gaming: settings.etfPool.gaming,
        newEnergy: settings.etfPool.newEnergy,
      });
      setNotifications(settings.notifications);
      setDisplaySettings(settings.display);
      setHasChanges(false);
    }
  };

  const renderParameterSlider = (
    label: string,
    param: keyof ParameterPreset,
    min: number,
    max: number,
    step: number,
    unit: string,
    info?: string
  ) => {
    const value = customParams[param] as number;
    
    return (
      <Box mb={3}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="subtitle2" fontWeight={500}>
              {label}
            </Typography>
            {info && (
              <Tooltip title={info}>
                <InfoIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
              </Tooltip>
            )}
          </Box>
          <Typography variant="body2" fontWeight={600}>
            {value}{unit}
          </Typography>
        </Box>
        <Slider
          value={value}
          onChange={(e, v) => handleParameterChange(param, v as number)}
          min={min}
          max={max}
          step={step}
          marks
          valueLabelDisplay="auto"
          valueLabelFormat={(v) => `${v}${unit}`}
        />
      </Box>
    );
  };

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" fontWeight={600}>
          Parameter Settings
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<RestoreIcon />}
            onClick={handleReset}
            disabled={!hasChanges}
          >
            Reset
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={!hasChanges || saveSettingsMutation.isPending}
          >
            Save Changes
          </Button>
        </Box>
      </Box>

      {hasChanges && (
        <Alert severity="warning" sx={{ mb: 3 }}>
          You have unsaved changes. Click "Save Changes" to apply them.
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Parameter Presets */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight={600}>
                Strategy Parameters
              </Typography>

              {/* Preset Selector */}
              <Box mb={3}>
                <Typography variant="subtitle2" gutterBottom>
                  Preset Configuration
                </Typography>
                <Stack direction="row" spacing={1}>
                  {Object.keys(PRESET_CONFIGS).map((preset) => (
                    <Chip
                      key={preset}
                      label={preset}
                      onClick={() => handlePresetChange(preset)}
                      color={selectedPreset === preset ? 'primary' : 'default'}
                      variant={selectedPreset === preset ? 'filled' : 'outlined'}
                    />
                  ))}
                  <Chip
                    label="Custom"
                    onClick={() => setSelectedPreset('Custom')}
                    color={selectedPreset === 'Custom' ? 'primary' : 'default'}
                    variant={selectedPreset === 'Custom' ? 'filled' : 'outlined'}
                  />
                </Stack>
              </Box>

              <Divider sx={{ my: 3 }} />

              {/* Custom Parameters */}
              {renderParameterSlider(
                'Stop Loss',
                'stopLoss',
                5,
                20,
                1,
                '%',
                'Maximum loss before position is closed'
              )}

              {renderParameterSlider(
                'Buffer',
                'buffer',
                1,
                5,
                0.5,
                '%',
                'Price buffer for order execution'
              )}

              {renderParameterSlider(
                'Min Holding Period',
                'minHolding',
                7,
                60,
                7,
                ' days',
                'Minimum days to hold a position'
              )}

              {renderParameterSlider(
                'Rebalance Bandwidth',
                'bandwidth',
                3,
                10,
                1,
                'pp',
                'Deviation threshold for rebalancing'
              )}

              {renderParameterSlider(
                'Correlation Threshold',
                'correlationThreshold',
                0.5,
                1.0,
                0.1,
                '',
                'Maximum allowed correlation between ETFs'
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* ETF Pool Management */}
        <Grid item xs={12} lg={6}>
          <Grid container spacing={3}>
            {/* ETF Selection */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    ETF Pool Management
                  </Typography>

                  {/* Gaming ETF Selection */}
                  <Box mb={3}>
                    <Typography variant="subtitle2" gutterBottom>
                      Gaming ETF (Choose One)
                    </Typography>
                    <RadioGroup
                      value={etfPool.gaming}
                      onChange={(e) => setEtfPool(prev => ({ ...prev, gaming: e.target.value }))}
                    >
                      {ETF_POOLS.gaming.map((etf) => (
                        <FormControlLabel
                          key={etf.code}
                          value={etf.code}
                          control={<Radio />}
                          label={`${etf.code} - ${etf.name}`}
                        />
                      ))}
                    </RadioGroup>
                  </Box>

                  {/* New Energy ETF Selection */}
                  <Box>
                    <Typography variant="subtitle2" gutterBottom>
                      New Energy ETF (Choose One)
                    </Typography>
                    <RadioGroup
                      value={etfPool.newEnergy}
                      onChange={(e) => setEtfPool(prev => ({ ...prev, newEnergy: e.target.value }))}
                    >
                      {ETF_POOLS.newEnergy.map((etf) => (
                        <FormControlLabel
                          key={etf.code}
                          value={etf.code}
                          control={<Radio />}
                          label={`${etf.code} - ${etf.name}`}
                        />
                      ))}
                    </RadioGroup>
                  </Box>
                </CardContent>
              </Card>
            </Grid>

            {/* Notifications */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    Notifications
                  </Typography>

                  <Stack spacing={2}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notifications.alerts}
                          onChange={(e) => setNotifications(prev => ({ ...prev, alerts: e.target.checked }))}
                        />
                      }
                      label="System Alerts"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notifications.trades}
                          onChange={(e) => setNotifications(prev => ({ ...prev, trades: e.target.checked }))}
                        />
                      }
                      label="Trade Executions"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notifications.rebalancing}
                          onChange={(e) => setNotifications(prev => ({ ...prev, rebalancing: e.target.checked }))}
                        />
                      }
                      label="Rebalancing Alerts"
                    />
                  </Stack>
                </CardContent>
              </Card>
            </Grid>

            {/* Display Settings */}
            <Grid item xs={12}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom fontWeight={600}>
                    Display Settings
                  </Typography>

                  <Stack spacing={2}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={displaySettings.theme === 'dark'}
                          onChange={(e) => setDisplaySettings(prev => ({ 
                            ...prev, 
                            theme: e.target.checked ? 'dark' : 'light' 
                          }))}
                        />
                      }
                      label="Dark Mode"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={displaySettings.compactMode}
                          onChange={(e) => setDisplaySettings(prev => ({ 
                            ...prev, 
                            compactMode: e.target.checked 
                          }))}
                        />
                      }
                      label="Compact Mode"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={displaySettings.showPremiums}
                          onChange={(e) => setDisplaySettings(prev => ({ 
                            ...prev, 
                            showPremiums: e.target.checked 
                          }))}
                        />
                      }
                      label="Show Premium Values"
                    />
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ParameterSettings;