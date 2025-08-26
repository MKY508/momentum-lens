import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Switch,
  FormControlLabel,
  Slider,
  Chip,
  CircularProgress,
  Alert,
  Tooltip,
  IconButton,
  Divider,
  Stack,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  CloudQueue as CloudIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Timer as TimerIcon,
  Speed as SpeedIcon,
} from '@mui/icons-material';
import { dataSourceManager } from '../../services/dataSourceManager';
import api from '../../services/api';
import toast from 'react-hot-toast';

interface DataSourceControlProps {
  onDataUpdate?: () => void;
  embedded?: boolean;
}

const DataSourceControl: React.FC<DataSourceControlProps> = ({
  onDataUpdate,
  embedded = false
}) => {
  const [selectedSource, setSelectedSource] = useState('akshare');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshInterval, setRefreshInterval] = useState(60);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
  const [availableSources, setAvailableSources] = useState<any[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<Record<string, boolean>>({});
  const [countdown, setCountdown] = useState(0);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const countdownRef = useRef<NodeJS.Timeout | null>(null);

  // 加载可用数据源
  useEffect(() => {
    loadDataSources();
  }, []);

  // 处理自动刷新
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      // 启动自动刷新
      startAutoRefresh();
      
      // 发送到后端
      api.market.setAutoRefresh(true, refreshInterval).catch(console.error);
    } else {
      // 停止自动刷新
      stopAutoRefresh();
      
      // 发送到后端
      api.market.setAutoRefresh(false, refreshInterval).catch(console.error);
    }

    return () => {
      stopAutoRefresh();
    };
  }, [autoRefresh, refreshInterval]);

  const loadDataSources = async () => {
    try {
      const response = await api.market.getDataSources();
      setAvailableSources(response.sources || []);
      setSelectedSource(response.active || 'akshare');
      setAutoRefresh(response.auto_refresh || false);
      setRefreshInterval(response.refresh_interval || 60);
      
      // 测试每个数据源的连接
      testAllConnections(response.sources || []);
    } catch (error) {
      console.error('Failed to load data sources:', error);
      toast.error('无法加载数据源列表');
    }
  };

  const testAllConnections = async (sources: any[]) => {
    const statuses: Record<string, boolean> = {};
    
    for (const source of sources) {
      try {
        const result = await api.market.testDataSource(source.id);
        statuses[source.id] = result.success;
      } catch {
        statuses[source.id] = false;
      }
    }
    
    setConnectionStatus(statuses);
  };

  const handleSourceChange = async (sourceId: string) => {
    setIsRefreshing(true);
    
    try {
      // 测试连接
      const testResult = await api.market.testDataSource(sourceId);
      
      if (!testResult.success) {
        toast.error(`无法连接到 ${sourceId}`);
        setIsRefreshing(false);
        return;
      }
      
      // 切换数据源
      const result = await api.market.setDataSource(sourceId);
      
      if (result.success) {
        setSelectedSource(sourceId);
        dataSourceManager.setActiveSource(sourceId);
        toast.success(result.message || `已切换到 ${sourceId}`);
        
        // 触发数据更新
        if (onDataUpdate) {
          onDataUpdate();
        }
      }
    } catch (error) {
      console.error('Failed to switch data source:', error);
      toast.error('切换数据源失败');
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    
    try {
      const result = await api.market.refreshData();
      
      if (result.success) {
        setLastRefreshTime(new Date());
        toast.success('数据已刷新');
        
        // 触发数据更新
        if (onDataUpdate) {
          onDataUpdate();
        }
        
        // 重置倒计时
        if (autoRefresh) {
          setCountdown(refreshInterval);
        }
      }
    } catch (error) {
      console.error('Failed to refresh data:', error);
      toast.error('刷新数据失败');
    } finally {
      setIsRefreshing(false);
    }
  };

  const startAutoRefresh = () => {
    // 清除现有定时器
    stopAutoRefresh();
    
    // 设置初始倒计时
    setCountdown(refreshInterval);
    
    // 启动倒计时更新
    countdownRef.current = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          handleManualRefresh();
          return refreshInterval;
        }
        return prev - 1;
      });
    }, 1000);
    
    // 启动自动刷新
    intervalRef.current = setInterval(() => {
      handleManualRefresh();
    }, refreshInterval * 1000);
  };

  const stopAutoRefresh = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    
    setCountdown(0);
  };

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`;
  };

  const getSourceStatus = (sourceId: string) => {
    const isConnected = connectionStatus[sourceId];
    if (isConnected === undefined) return 'unknown';
    return isConnected ? 'connected' : 'disconnected';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected': return 'success';
      case 'disconnected': return 'error';
      default: return 'warning';
    }
  };

  if (embedded) {
    // 嵌入式简洁版本
    return (
      <Box display="flex" alignItems="center" gap={2}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <Select
            value={selectedSource}
            onChange={(e) => handleSourceChange(e.target.value)}
            disabled={isRefreshing}
          >
            {availableSources.map(source => (
              <MenuItem key={source.id} value={source.id}>
                <Box display="flex" alignItems="center" gap={1}>
                  {getSourceStatus(source.id) === 'connected' && 
                    <CheckCircleIcon fontSize="small" color="success" />}
                  {source.name}
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        <FormControlLabel
          control={
            <Switch
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              size="small"
            />
          }
          label={autoRefresh && countdown > 0 ? formatCountdown(countdown) : "自动刷新"}
        />
        
        <IconButton 
          onClick={handleManualRefresh} 
          disabled={isRefreshing}
          size="small"
        >
          {isRefreshing ? (
            <CircularProgress size={20} />
          ) : (
            <RefreshIcon />
          )}
        </IconButton>
      </Box>
    );
  }

  // 完整控制面板
  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        数据源控制
      </Typography>
      
      <Divider sx={{ my: 2 }} />
      
      <Stack spacing={3}>
        {/* 数据源选择 */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            数据源选择
          </Typography>
          <FormControl fullWidth>
            <InputLabel>选择数据源</InputLabel>
            <Select
              value={selectedSource}
              label="选择数据源"
              onChange={(e) => handleSourceChange(e.target.value)}
              disabled={isRefreshing}
            >
              {availableSources.map(source => (
                <MenuItem key={source.id} value={source.id}>
                  <Box 
                    display="flex" 
                    alignItems="center" 
                    justifyContent="space-between" 
                    width="100%"
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      {getSourceStatus(source.id) === 'connected' && 
                        <CheckCircleIcon fontSize="small" color="success" />}
                      {getSourceStatus(source.id) === 'disconnected' && 
                        <ErrorIcon fontSize="small" color="error" />}
                      <Typography>{source.name}</Typography>
                    </Box>
                    <Box display="flex" gap={1}>
                      {source.type === 'free' && (
                        <Chip label="免费" size="small" color="success" />
                      )}
                      <Chip 
                        label={source.rate_limit || '无限制'} 
                        size="small" 
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* 自动刷新设置 */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            刷新设置
          </Typography>
          
          <FormControlLabel
            control={
              <Switch
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
            }
            label="启用自动刷新"
          />
          
          {autoRefresh && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" gutterBottom>
                刷新间隔: {refreshInterval} 秒
              </Typography>
              <Slider
                value={refreshInterval}
                onChange={(e, value) => setRefreshInterval(value as number)}
                min={10}
                max={300}
                step={10}
                marks={[
                  { value: 10, label: '10秒' },
                  { value: 60, label: '1分钟' },
                  { value: 120, label: '2分钟' },
                  { value: 300, label: '5分钟' },
                ]}
                valueLabelDisplay="auto"
              />
              
              {countdown > 0 && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <TimerIcon fontSize="small" />
                    下次刷新: {formatCountdown(countdown)}
                  </Box>
                </Alert>
              )}
            </Box>
          )}
        </Box>

        {/* 手动刷新按钮 */}
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Button
            variant="contained"
            startIcon={isRefreshing ? <CircularProgress size={20} /> : <RefreshIcon />}
            onClick={handleManualRefresh}
            disabled={isRefreshing}
          >
            立即刷新
          </Button>
          
          {lastRefreshTime && (
            <Typography variant="caption" color="text.secondary">
              最后刷新: {lastRefreshTime.toLocaleTimeString()}
            </Typography>
          )}
        </Box>

        {/* 连接状态 */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            连接状态
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {availableSources.map(source => (
              <Chip
                key={source.id}
                icon={
                  getSourceStatus(source.id) === 'connected' ? 
                    <CheckCircleIcon /> : 
                    getSourceStatus(source.id) === 'disconnected' ?
                    <ErrorIcon /> :
                    <CloudIcon />
                }
                label={source.name}
                color={getStatusColor(getSourceStatus(source.id)) as any}
                variant={source.id === selectedSource ? 'filled' : 'outlined'}
                size="small"
              />
            ))}
          </Box>
        </Box>
      </Stack>
    </Paper>
  );
};

export default DataSourceControl;