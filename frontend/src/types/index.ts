// Core type definitions for Momentum Lens

export interface ETF {
  code: string;
  name: string;
  type?: string;
  premium?: number;
  price?: number;
  volume?: number;
  spread?: number;
  status?: 'NORMAL' | 'SUSPENDED' | 'MERGED' | 'DELISTED' | 'NO_DATA';
  statusMessage?: string;
}

export interface Decision {
  firstLeg: {
    code: string;
    name: string;
    score: number;
    status?: 'NORMAL' | 'SUSPENDED' | 'MERGED' | 'DELISTED' | 'NO_DATA';
    statusMessage?: string;
  };
  secondLeg: {
    code: string;
    name: string;
    score: number;
    status?: 'NORMAL' | 'SUSPENDED' | 'MERGED' | 'DELISTED' | 'NO_DATA';
    statusMessage?: string;
  };
  weights: {
    trial: number;
    full: number;
  };
  iopvBands: {
    lower: number;
    upper: number;
  };
  qualifications: {
    buffer: boolean;
    minHolding: boolean;
    correlation: boolean;
    legLimit: boolean;
    // Additional details for display
    bufferValue?: number;
    bufferThreshold?: number;
    minHoldingDays?: number;
    minHoldingRequired?: number;
    correlationValue?: number;
    correlationThreshold?: number;
    currentLegs?: number;
    maxLegs?: number;
  };
  qdiiStatus: {
    code: string;
    premium: number;
    status: 'OK' | 'WARNING' | 'ERROR';
  };
  timestamp: string;
}

export interface MarketIndicator {
  yearline: {
    status: 'ABOVE' | 'BELOW';
    value: number;
    ma200: number;
    deviation?: number; // (Close/MA200 - 1) × 100%
  };
  atr: {
    value: number;
    status: 'LOW' | 'MEDIUM' | 'HIGH';
  };
  chop: {
    value: number;
    status: 'TRENDING' | 'CHOPPY';
    inBandDays?: number; // Days within MA200 ±3% band
  };
  marketRegime?: 'TRENDING' | 'CHOPPY'; // Overall market regime
}

export interface Holding {
  code: string;
  name: string;
  targetWeight: number;
  currentWeight: number;
  deviation: number;
  shares: number;
  value: number;
  premium?: number;
}

export interface MomentumETF {
  code: string;
  name: string;
  r60: number;
  r120: number;
  r60_nominal?: number;  // 名义收益率（不含分红）
  r120_nominal?: number; // 名义收益率（不含分红）
  score: number;
  volume: number;
  spread: number;
  type: string;
  qualified: boolean;
  isHolding?: boolean;
  holdingStartDate?: string | Date;
  has_dividend?: boolean;    // 是否有分红
  dividend_impact?: number;   // 分红影响百分比
  adjusted?: boolean;         // 是否是调整后的数据
}

export interface ParameterPreset {
  name: '进攻' | '均衡' | '保守' | '自定义';
  stopLoss: number;
  buffer: number;
  minHolding: number;
  bandwidth: number;
  correlationThreshold: number;
}

export interface TradeLog {
  id: string;
  timestamp: string;
  type: 'BUY' | 'SELL';
  code: string;
  name: string;
  shares: number;
  price: number;
  amount: number;
  slippage: number;
  implementationShortfall?: number; // IS = (成交价/下单IOPV - 1) × 100%
  status: 'EXECUTED' | 'PENDING' | 'CANCELLED';
  // Enhanced decision traceability fields for replay
  iopvAtOrder?: number;          // 下单时的IOPV值
  iopvBandLow?: number;          // IOPV带宽下限
  iopvBandHigh?: number;         // IOPV带宽上限
  correlationWithTop1?: number;  // ρ(Top1) - 与第一名的相关性
  scoreOld?: number;             // 原始分数
  scoreNew?: number;             // 新分数
  scoreDiff?: number;            // 分数差值
  bufferThreshold?: number;      // Buffer阈值
  minHoldOk?: boolean;           // 最小持仓期是否达标
  regimeSnapshot?: {             // 市场状态快照
    yearline: 'ABOVE' | 'BELOW';
    choppy: boolean;
    atr: number;
    inBandDays: number;
  };
  idempotencyKey?: string;       // 幂等键 - 防重复下单标识
}

export interface Alert {
  id: string;
  timestamp: string;
  type: 'INFO' | 'WARNING' | 'ERROR' | 'SUCCESS';
  title: string;
  message: string;
  read: boolean;
}

export interface PerformanceMetrics {
  monthlyIS: number;
  turnoverEfficiency: number;
  maxDrawdown: number;
  calmarRatio: number;
  ytdReturn: number;
  volatility: number;
  monthlyReturn?: number;
  monthlyTurnover?: number;
  unitTurnoverReturn?: number; // monthlyReturn / monthlyTurnover
  winRate?: number;
  sharpeRatio?: number;
}

export interface Settings {
  preset: ParameterPreset;
  etfPool: {
    gaming: '516010' | '159869';
    newEnergy: '516160' | '515790' | '515030';
    excludedETFs: string[];
  };
  notifications: {
    alerts: boolean;
    trades: boolean;
    rebalancing: boolean;
  };
  display: {
    theme: 'light' | 'dark';
    compactMode: boolean;
    showPremiums: boolean;
  };
  marketRegime?: 'TRENDING' | 'CHOPPY'; // Current market regime for parameter locking
}

export interface PriceUpdate {
  code: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: string;
}

export interface CorrelationItem {
  etf1: string;
  etf2: string;
  correlation: number;
}

export interface CorrelationMatrix {
  etfs: string[];
  values: number[][];
  correlations?: CorrelationItem[];
}

export interface DCASchedule {
  nextDate: string;
  amount: number;
  frequency: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY';
  enabled: boolean;
}