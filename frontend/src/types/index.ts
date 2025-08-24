// Core type definitions for Momentum Lens

export interface ETF {
  code: string;
  name: string;
  type?: string;
  premium?: number;
  price?: number;
  volume?: number;
  spread?: number;
}

export interface Decision {
  firstLeg: {
    code: string;
    name: string;
    score: number;
  };
  secondLeg: {
    code: string;
    name: string;
    score: number;
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
  };
  atr: {
    value: number;
    status: 'LOW' | 'MEDIUM' | 'HIGH';
  };
  chop: {
    value: number;
    status: 'TRENDING' | 'CHOPPY';
  };
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
  score: number;
  volume: number;
  spread: number;
  type: string;
  qualified: boolean;
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
  status: 'EXECUTED' | 'PENDING' | 'CANCELLED';
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
}

export interface PriceUpdate {
  code: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: string;
}

export interface CorrelationMatrix {
  etfs: string[];
  values: number[][];
}

export interface DCASchedule {
  nextDate: string;
  amount: number;
  frequency: 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY';
  enabled: boolean;
}