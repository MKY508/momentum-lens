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
  Tabs,
  Tab,
} from '@mui/material';
import {
  Save as SaveIcon,
  Restore as RestoreIcon,
  Info as InfoIcon,
  Warning as WarningIcon,
  Api as ApiIcon,
  Settings as SettingsIcon,
  Dashboard as DashboardIcon,
} from '@mui/icons-material';
import { useQuery, useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import api from '../../services/api';
import { Settings, ParameterPreset } from '../../types';
import APIConfiguration from './APIConfiguration';
import APIDocumentation from './APIDocumentation';

const PRESET_CONFIGS: Record<string, ParameterPreset> = {
  '进攻': {
    name: '进攻',
    stopLoss: 10,
    buffer: 2,
    minHolding: 14,
    bandwidth: 5,
    correlationThreshold: 0.8,
  },
  '均衡': {
    name: '均衡',
    stopLoss: 12,
    buffer: 3,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
  '保守': {
    name: '保守',
    stopLoss: 15,
    buffer: 4,
    minHolding: 28,
    bandwidth: 7,
    correlationThreshold: 0.8,
  },
};

const ETF_POOLS = {
  gaming: [
    { code: '516010', name: '游戏动漫ETF' },
    { code: '159869', name: '游戏ETF' },
  ],
  newEnergy: [
    { code: '516160', name: '新能源ETF' },
    { code: '515790', name: '光伏ETF' },
    { code: '515030', name: '新能源车ETF' },
  ],
};

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
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box>{children}</Box>}
    </div>
  );
}

const ParameterSettings: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [selectedPreset, setSelectedPreset] = useState<string>('均衡');
  const [customParams, setCustomParams] = useState<ParameterPreset>(PRESET_CONFIGS['均衡']);
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
  });

  // Update state when settings data changes
  useEffect(() => {
    if (settings) {
      setSelectedPreset(settings.preset?.name || '均衡');
      setCustomParams(settings.preset || PRESET_CONFIGS['均衡']);
      setEtfPool({
        gaming: settings.etfPool?.gaming || '516010',
        newEnergy: settings.etfPool?.newEnergy || '516160',
      });
      setNotifications(settings.notifications || { stopLoss: true, yearline: true });
      setDisplaySettings(settings.display || { darkMode: false, showCharts: true, showPremiums: true });
    }
  }, [settings]);

  // Save settings mutation
  const saveSettingsMutation = useMutation({
    mutationFn: (newSettings: Partial<Settings>) => api.config.updateSettings(newSettings),
    onSuccess: () => {
      toast.success('设置保存成功');
      setHasChanges(false);
      refetch();
    },
    onError: (error) => {
      toast.error('设置保存失败');
      console.error('Settings save error:', error);
    },
  });

  // Track changes
  useEffect(() => {
    if (settings) {
      const hasParamChanges = 
        JSON.stringify(customParams) !== JSON.stringify(settings?.preset) ||
        selectedPreset !== settings?.preset?.name;
      
      const hasEtfChanges = 
        etfPool.gaming !== settings?.etfPool?.gaming ||
        etfPool.newEnergy !== settings?.etfPool?.newEnergy;
      
      const hasNotificationChanges = 
        JSON.stringify(notifications) !== JSON.stringify(settings?.notifications);
      
      const hasDisplayChanges = 
        JSON.stringify(displaySettings) !== JSON.stringify(settings?.display);

      setHasChanges(hasParamChanges || hasEtfChanges || hasNotificationChanges || hasDisplayChanges);
    }
  }, [customParams, selectedPreset, etfPool, notifications, displaySettings, settings]);

  const handlePresetChange = (preset: string) => {
    setSelectedPreset(preset);
    if (preset !== '自定义' && PRESET_CONFIGS[preset]) {
      setCustomParams(PRESET_CONFIGS[preset]);
    }
  };

  const handleParameterChange = (param: keyof ParameterPreset, value: number) => {
    setCustomParams(prev => ({ ...prev, [param]: value }));
    setSelectedPreset('自定义');
  };

  const handleSave = () => {
    const newSettings: Partial<Settings> = {
      preset: { ...customParams, name: selectedPreset as any },
      etfPool: {
        gaming: etfPool.gaming as any,
        newEnergy: etfPool.newEnergy as any,
        excludedETFs: settings?.etfPool?.excludedETFs || [],
      },
      notifications,
      display: displaySettings,
    };
    
    saveSettingsMutation.mutate(newSettings);
  };

  const handleReset = () => {
    if (settings) {
      setSelectedPreset(settings.preset?.name || '均衡');
      setCustomParams(settings.preset || PRESET_CONFIGS['均衡']);
      setEtfPool({
        gaming: settings.etfPool?.gaming || '516010',
        newEnergy: settings.etfPool?.newEnergy || '516160',
      });
      setNotifications(settings.notifications || { stopLoss: true, yearline: true });
      setDisplaySettings(settings.display || { darkMode: false, showCharts: true, showPremiums: true });
      setHasChanges(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
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
          参数设置
        </Typography>
        {tabValue === 0 && (
          <Box display="flex" gap={2}>
            <Button
              variant="outlined"
              startIcon={<RestoreIcon />}
              onClick={handleReset}
              disabled={!hasChanges}
            >
              恢复默认
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={!hasChanges || saveSettingsMutation.isPending}
            >
              保存设置
            </Button>
          </Box>
        )}
      </Box>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange} aria-label="settings tabs">
          <Tab icon={<SettingsIcon />} label="参数配置" />
          <Tab icon={<ApiIcon />} label="API配置" />
          <Tab icon={<InfoIcon />} label="文档说明" />
        </Tabs>
      </Box>

      {/* Tab Panels */}
      <TabPanel value={tabValue} index={0}>
        {hasChanges && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            您有未保存的更改。请点击"保存设置"以应用更改。
          </Alert>
        )}

        <Grid container spacing={3}>
        {/* Parameter Presets */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom fontWeight={600}>
                策略参数
              </Typography>

              {/* Preset Selector */}
              <Box mb={3}>
                <Typography variant="subtitle2" gutterBottom>
                  预设配置
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
                    label="自定义"
                    onClick={() => setSelectedPreset('自定义')}
                    color={selectedPreset === '自定义' ? 'primary' : 'default'}
                    variant={selectedPreset === '自定义' ? 'filled' : 'outlined'}
                  />
                </Stack>
              </Box>

              <Divider sx={{ my: 3 }} />

              {/* Custom Parameters */}
              {renderParameterSlider(
                '止损',
                'stopLoss',
                5,
                20,
                1,
                '%',
                '触发止损的最大亏损比例'
              )}

              {renderParameterSlider(
                '缓冲区',
                'buffer',
                1,
                5,
                0.5,
                '%',
                '限价单执行时的价格缓冲区间'
              )}

              {renderParameterSlider(
                '最短持有期',
                'minHolding',
                7,
                60,
                7,
                ' 天',
                '持仓不轮动的最短天数要求'
              )}

              {renderParameterSlider(
                '再平衡带宽',
                'bandwidth',
                3,
                10,
                1,
                'pp',
                '触发再平衡操作的偏差带宽'
              )}

              {renderParameterSlider(
                '相关性阈值',
                'correlationThreshold',
                0.5,
                1.0,
                0.1,
                '',
                '两腿ETF之间的最大相关系数阈值'
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
                    ETF池管理
                  </Typography>

                  {/* Gaming ETF Selection */}
                  <Box mb={3}>
                    <Typography variant="subtitle2" gutterBottom>
                      成长线ETF（二选一）
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
                      电新链ETF（三选一）
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
                    通知设置
                  </Typography>

                  <Stack spacing={2}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notifications.alerts}
                          onChange={(e) => setNotifications(prev => ({ ...prev, alerts: e.target.checked }))}
                        />
                      }
                      label="系统预警"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notifications.trades}
                          onChange={(e) => setNotifications(prev => ({ ...prev, trades: e.target.checked }))}
                        />
                      }
                      label="交易执行"
                    />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={notifications.rebalancing}
                          onChange={(e) => setNotifications(prev => ({ ...prev, rebalancing: e.target.checked }))}
                        />
                      }
                      label="再平衡提醒"
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
                    显示设置
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
                      label="深色模式"
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
                      label="紧凑模式"
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
                      label="显示溢价值"
                    />
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </Grid>
      </Grid>
      </TabPanel>

      {/* API Configuration Tab */}
      <TabPanel value={tabValue} index={1}>
        <APIConfiguration />
      </TabPanel>

      {/* Documentation Tab */}
      <TabPanel value={tabValue} index={2}>
        <APIDocumentation />
      </TabPanel>
    </Box>
  );
};

export default ParameterSettings;