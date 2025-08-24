import React, { useState, useEffect } from 'react';
import {
  Box,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Typography,
  Divider,
  CircularProgress,
  Tooltip,
  Badge,
  Alert,
  Collapse,
} from '@mui/material';
import {
  CloudQueue as CloudIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  ArrowDropDown as ArrowDropDownIcon,
  Refresh as RefreshIcon,
  Speed as SpeedIcon,
  SignalCellularAlt as SignalIcon,
} from '@mui/icons-material';
import { dataSourceManager, DataSource } from '../../services/dataSourceManager';
import toast from 'react-hot-toast';

interface DataSourceStatusProps {
  compact?: boolean;
  showDetails?: boolean;
  onSourceChange?: (sourceId: string) => void;
}

const DataSourceStatus: React.FC<DataSourceStatusProps> = ({
  compact = false,
  showDetails = true,
  onSourceChange
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [activeSource, setActiveSource] = useState<DataSource | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<Map<string, boolean>>(new Map());
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showAlert, setShowAlert] = useState(false);
  const [alertMessage, setAlertMessage] = useState('');
  const [lastUpdateTime, setLastUpdateTime] = useState<Date>(new Date());

  useEffect(() => {
    updateStatus();
    const interval = setInterval(updateStatus, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const updateStatus = () => {
    const source = dataSourceManager.getActiveSource();
    setActiveSource(source);
    setConnectionStatus(dataSourceManager.getConnectionStatus());
    setLastUpdateTime(new Date());
  };

  const handleClick = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleSourceSelect = async (sourceId: string) => {
    handleClose();
    
    // Test connection first
    setIsRefreshing(true);
    const isConnected = await dataSourceManager.testConnection(sourceId);
    
    if (isConnected) {
      dataSourceManager.setActiveSource(sourceId);
      setActiveSource(dataSourceManager.getActiveSource());
      
      if (onSourceChange) {
        onSourceChange(sourceId);
      }
      
      toast.success(`Switched to ${dataSourceManager.getSourceById(sourceId)?.name}`);
    } else {
      toast.error(`Failed to connect to ${dataSourceManager.getSourceById(sourceId)?.name}`);
      setAlertMessage(`Unable to connect to ${dataSourceManager.getSourceById(sourceId)?.name}. Please check your configuration.`);
      setShowAlert(true);
    }
    
    setIsRefreshing(false);
    updateStatus();
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    
    // Test current source
    if (activeSource) {
      const isConnected = await dataSourceManager.testConnection(activeSource.id);
      if (!isConnected) {
        setAlertMessage(`Connection to ${activeSource.name} lost. Switching to fallback...`);
        setShowAlert(true);
        
        // Try to find a working fallback
        const sources = dataSourceManager.getAllSources();
        for (const source of sources.sort((a, b) => a.priority - b.priority)) {
          const connected = await dataSourceManager.testConnection(source.id);
          if (connected) {
            dataSourceManager.setActiveSource(source.id);
            setActiveSource(source);
            toast.info(`Switched to ${source.name} (fallback)`);
            break;
          }
        }
      } else {
        toast.success('Connection verified');
      }
    }
    
    updateStatus();
    setIsRefreshing(false);
  };

  const getStatusIcon = () => {
    if (isRefreshing) {
      return <CircularProgress size={16} />;
    }

    const isConnected = activeSource ? connectionStatus.get(activeSource.id) : false;
    
    if (isConnected) {
      return <CheckCircleIcon fontSize="small" color="success" />;
    } else if (isConnected === false) {
      return <ErrorIcon fontSize="small" color="error" />;
    } else {
      return <WarningIcon fontSize="small" color="warning" />;
    }
  };

  const getStatusColor = () => {
    const isConnected = activeSource ? connectionStatus.get(activeSource.id) : false;
    
    if (isConnected) {
      return 'success';
    } else if (isConnected === false) {
      return 'error';
    } else {
      return 'warning';
    }
  };

  const getLatencyIndicator = () => {
    if (!activeSource?.averageLatency) return null;
    
    const latency = activeSource.averageLatency;
    let color = 'success';
    let strength = 3;
    
    if (latency > 1000) {
      color = 'error';
      strength = 1;
    } else if (latency > 500) {
      color = 'warning';
      strength = 2;
    }
    
    return (
      <Tooltip title={`Latency: ${latency}ms`}>
        <Box display="flex" alignItems="center">
          <SignalIcon 
            fontSize="small" 
            color={color as any}
            style={{ transform: `scaleX(${strength === 1 ? 0.3 : strength === 2 ? 0.6 : 1})` }}
          />
        </Box>
      </Tooltip>
    );
  };

  if (compact) {
    return (
      <Box display="flex" alignItems="center" gap={1}>
        <Tooltip title={activeSource ? `Data: ${activeSource.name}` : 'No data source'}>
          <Badge
            color={getStatusColor() as any}
            variant="dot"
            invisible={!activeSource}
          >
            <CloudIcon fontSize="small" />
          </Badge>
        </Tooltip>
        
        {activeSource && (
          <Typography variant="caption" color="text.secondary">
            {activeSource.name}
          </Typography>
        )}
      </Box>
    );
  }

  return (
    <>
      <Box display="flex" alignItems="center" gap={1}>
        <Chip
          icon={getStatusIcon()}
          label={
            <Box display="flex" alignItems="center" gap={0.5}>
              <Typography variant="body2">
                {activeSource ? activeSource.name : 'No Source'}
              </Typography>
              {activeSource?.type === 'free' && (
                <Chip size="small" label="Free" color="success" style={{ height: 16, fontSize: 10 }} />
              )}
              {getLatencyIndicator()}
            </Box>
          }
          onClick={handleClick}
          onDelete={handleClick}
          deleteIcon={<ArrowDropDownIcon />}
          color={getStatusColor() as any}
          variant="outlined"
        />
        
        <Tooltip title="Refresh connection">
          <IconButton size="small" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      <Collapse in={showAlert}>
        <Alert 
          severity="warning" 
          onClose={() => setShowAlert(false)}
          sx={{ mt: 1 }}
        >
          {alertMessage}
        </Alert>
      </Collapse>

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleClose}
        PaperProps={{
          style: {
            maxHeight: 400,
            width: 300,
          },
        }}
      >
        <Box px={2} py={1}>
          <Typography variant="subtitle2" color="text.secondary">
            Select Data Source
          </Typography>
        </Box>
        
        <Divider />
        
        {dataSourceManager.getAllSources().map((source) => {
          const isConnected = connectionStatus.get(source.id);
          const isActive = source.id === activeSource?.id;
          
          return (
            <MenuItem
              key={source.id}
              onClick={() => handleSourceSelect(source.id)}
              selected={isActive}
            >
              <Box display="flex" alignItems="center" justifyContent="space-between" width="100%">
                <Box display="flex" alignItems="center" gap={1}>
                  {isConnected === true && <CheckCircleIcon fontSize="small" color="success" />}
                  {isConnected === false && <ErrorIcon fontSize="small" color="error" />}
                  {isConnected === undefined && <WarningIcon fontSize="small" color="warning" />}
                  
                  <Box>
                    <Typography variant="body2">
                      {source.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {source.rateLimit || 'No rate limit'}
                    </Typography>
                  </Box>
                </Box>
                
                <Box display="flex" gap={0.5}>
                  {source.type === 'free' && (
                    <Chip size="small" label="Free" color="success" style={{ height: 20, fontSize: 10 }} />
                  )}
                  {isActive && (
                    <Chip size="small" label="Active" color="primary" style={{ height: 20, fontSize: 10 }} />
                  )}
                </Box>
              </Box>
            </MenuItem>
          );
        })}
        
        <Divider />
        
        {showDetails && (
          <Box px={2} py={1}>
            <Typography variant="caption" color="text.secondary">
              Last updated: {lastUpdateTime.toLocaleTimeString()}
            </Typography>
          </Box>
        )}
      </Menu>
    </>
  );
};

export default DataSourceStatus;