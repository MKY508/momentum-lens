import React from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  LinearProgress,
  Chip,
  Stack,
  Grid,
  Button,
  Tooltip,
  Alert,
  Divider,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Schedule as ScheduleIcon,
  Warning as WarningIcon,
  CheckCircle as CheckIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';

interface CoreHolding {
  code: string;
  name: string;
  currentWeight: number;
  targetWeight: number;
  deviation: number;
}

interface CoreSnapshotProps {
  holdings?: CoreHolding[];
  yearline?: {
    status: string;
    deviation?: number;
    ma200?: number;
    currentPrice?: number;
    unlockDate?: string;
  };
  nextDCA?: {
    date: string;
    window1: string;
    window2: string;
    amount: number;
  };
  qdiiStatus?: {
    code: string;
    premium: number;
    status: string;
    alternativeCode?: string;
  };
}

const CoreSnapshot: React.FC<CoreSnapshotProps> = ({
  holdings = [
    { code: '510300', name: '沪深300', currentWeight: 35.2, targetWeight: 33.3, deviation: 1.9 },
    { code: '510880', name: '红利ETF', currentWeight: 31.5, targetWeight: 33.3, deviation: -1.8 },
    { code: '511990', name: '国债ETF', currentWeight: 18.8, targetWeight: 16.7, deviation: 2.1 },
    { code: '518880', name: '黄金ETF', currentWeight: 8.2, targetWeight: 10.0, deviation: -1.8 },
    { code: '513500', name: '标普500', currentWeight: 6.3, targetWeight: 6.7, deviation: -0.4 },
  ],
  yearline = {
    status: 'ABOVE',
    deviation: 1.4,
    ma200: 3450,
    currentPrice: 3498,
    unlockDate: '2024-08-23',
  },
  nextDCA = {
    date: '2024-08-27',
    window1: '10:30',
    window2: '14:00',
    amount: 20000,
  },
  qdiiStatus = {
    code: '513500',
    premium: 1.5,
    status: 'OK',
    alternativeCode: '511990',
  },
}) => {
  
  // 生成一键调仓建议
  const generateRebalanceSuggestion = () => {
    const suggestions = holdings
      .filter(h => Math.abs(h.deviation) > 5)
      .map(h => {
        const targetDeviation = h.deviation > 0 ? 2 : -2; // 回到目标±2pp
        const adjustment = h.currentWeight - (h.targetWeight + targetDeviation);
        return {
          code: h.code,
          name: h.name,
          action: adjustment > 0 ? 'SELL' : 'BUY',
          amount: Math.abs(adjustment),
        };
      });
    
    if (suggestions.length > 0) {
      console.log('调仓建议:', suggestions);
      // 这里可以调用API或显示对话框
    }
  };

  // 权重偏离条形图
  const WeightBar = ({ holding }: { holding: CoreHolding }) => {
    const isOverweight = holding.deviation > 0;
    const barColor = Math.abs(holding.deviation) > 5 ? '#f44336' : 
                     Math.abs(holding.deviation) > 2 ? '#ff9800' : '#4caf50';
    
    return (
      <Box sx={{ mb: 1.5 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 0.5 }}>
          <Typography variant="caption" sx={{ fontWeight: 600 }}>
            {holding.code}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {holding.currentWeight.toFixed(1)}% / {holding.targetWeight.toFixed(1)}%
            <span style={{ color: barColor, marginLeft: 4 }}>
              ({isOverweight ? '+' : ''}{holding.deviation.toFixed(1)}pp)
            </span>
          </Typography>
        </Stack>
        <Box sx={{ position: 'relative', height: 8, bgcolor: 'grey.200', borderRadius: 1 }}>
          {/* 目标范围带（±5pp） */}
          <Box
            sx={{
              position: 'absolute',
              left: `${Math.max(0, (holding.targetWeight - 5) / 40 * 100)}%`,
              width: `${10 / 40 * 100}%`,
              height: '100%',
              bgcolor: 'grey.300',
              opacity: 0.5,
            }}
          />
          {/* 当前权重条 */}
          <Box
            sx={{
              position: 'absolute',
              left: 0,
              width: `${holding.currentWeight / 40 * 100}%`,
              height: '100%',
              bgcolor: barColor,
              borderRadius: 1,
              transition: 'width 0.3s ease',
            }}
          />
          {/* 目标权重标记 */}
          <Box
            sx={{
              position: 'absolute',
              left: `${holding.targetWeight / 40 * 100}%`,
              width: 2,
              height: '100%',
              bgcolor: 'grey.700',
            }}
          />
        </Box>
      </Box>
    );
  };

  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Stack spacing={2}>
          {/* 标题行 */}
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <Typography variant="h6" component="div">
              Core 快照
            </Typography>
            {holdings.some(h => Math.abs(h.deviation) > 5) && (
              <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={<WarningIcon />}
                onClick={generateRebalanceSuggestion}
              >
                一键建议
              </Button>
            )}
          </Stack>

          {/* 权重偏离条 */}
          <Box>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              权重偏离（当前 / 目标）
            </Typography>
            {holdings.map(holding => (
              <WeightBar key={holding.code} holding={holding} />
            ))}
          </Box>

          <Divider />

          {/* 年线状态 */}
          <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="subtitle2" color="text.secondary">
                年线状态
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                {yearline.status === 'ABOVE' ? (
                  <Chip
                    icon={<TrendingUpIcon />}
                    label={`在上 (+${yearline.deviation?.toFixed(1)}%)`}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                ) : (
                  <Chip
                    icon={<TrendingDownIcon />}
                    label={`在下 (${yearline.deviation?.toFixed(1)}%)`}
                    size="small"
                    color="error"
                    variant="outlined"
                  />
                )}
                <Typography variant="caption" color="text.secondary">
                  {yearline.currentPrice?.toFixed(0)} / {yearline.ma200?.toFixed(0)}
                </Typography>
              </Stack>
            </Stack>
            {yearline.unlockDate && (
              <Typography variant="caption" color="text.secondary">
                解锁于 {format(new Date(yearline.unlockDate), 'MM/dd', { locale: zhCN })}
              </Typography>
            )}
          </Box>

          <Divider />

          {/* 下次DCA */}
          <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="subtitle2" color="text.secondary">
                下次 DCA
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <ScheduleIcon fontSize="small" color="action" />
                <Typography variant="body2">
                  {format(new Date(nextDCA.date), 'MM/dd')}
                </Typography>
                <Chip
                  label={`${nextDCA.window1} / ${nextDCA.window2}`}
                  size="small"
                  variant="outlined"
                />
              </Stack>
            </Stack>
            <Typography variant="caption" color="text.secondary">
              金额：¥{nextDCA.amount.toLocaleString()}
            </Typography>
          </Box>

          <Divider />

          {/* QDII状态 */}
          <Box>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="subtitle2" color="text.secondary">
                QDII 状态
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Typography variant="body2">
                  {qdiiStatus.code}
                </Typography>
                {qdiiStatus.premium <= 2 ? (
                  <Chip
                    icon={<CheckIcon />}
                    label={`溢价 ${qdiiStatus.premium.toFixed(1)}%`}
                    size="small"
                    color="success"
                    variant="outlined"
                  />
                ) : (
                  <Tooltip title={`溢价≥3%，建议改买 ${qdiiStatus.alternativeCode}`}>
                    <Chip
                      icon={<WarningIcon />}
                      label={`溢价 ${qdiiStatus.premium.toFixed(1)}%`}
                      size="small"
                      color="warning"
                      variant="outlined"
                    />
                  </Tooltip>
                )}
              </Stack>
            </Stack>
            {qdiiStatus.premium >= 3 && (
              <Alert severity="warning" sx={{ mt: 1, py: 0 }}>
                <Typography variant="caption">
                  溢价过高，建议改买 {qdiiStatus.alternativeCode}
                </Typography>
              </Alert>
            )}
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default CoreSnapshot;