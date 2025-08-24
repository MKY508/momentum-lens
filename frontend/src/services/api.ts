import axios, { AxiosInstance } from 'axios';
import {
  Decision,
  MarketIndicator,
  Holding,
  MomentumETF,
  TradeLog,
  Alert,
  PerformanceMetrics,
  Settings,
  PriceUpdate,
  CorrelationMatrix,
  DCASchedule,
  ParameterPreset
} from '../types';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
axiosInstance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Decision endpoints
  decisions: {
    calculate: (params?: Partial<ParameterPreset>): Promise<Decision> =>
      axiosInstance.post('/api/decisions/calculate', params),
    getCurrent: (): Promise<Decision> =>
      axiosInstance.get('/api/decisions/current'),
    getHistory: (limit = 10): Promise<Decision[]> =>
      axiosInstance.get('/api/decisions/history', { params: { limit } }),
  },

  // Market data endpoints
  market: {
    getIndicators: (): Promise<MarketIndicator> =>
      axiosInstance.get('/api/market/indicators'),
    getETFPrices: (codes: string[]): Promise<PriceUpdate[]> =>
      axiosInstance.get('/api/market/etf-prices', { params: { codes: codes.join(',') } }),
    getMomentumRankings: (): Promise<MomentumETF[]> =>
      axiosInstance.get('/api/market/momentum-rankings'),
    getCorrelationMatrix: (anchor: string): Promise<CorrelationMatrix> =>
      axiosInstance.get('/api/market/correlation', { params: { anchor } }),
    getHS300Chart: (period = '1Y'): Promise<any> =>
      axiosInstance.get('/api/market/hs300-chart', { params: { period } }),
    
    // Data source endpoints
    testDataSource: (sourceId: string, apiKey?: string): Promise<{ success: boolean; latency?: number }> =>
      axiosInstance.post('/api/market/test-source', { sourceId, apiKey }),
    fetchFromSource: (sourceId: string, symbol: string, apiKey?: string): Promise<{ data: any }> =>
      axiosInstance.post('/api/market/fetch', { sourceId, symbol, apiKey }),
    fetchBatch: (sourceId: string, symbols: string[]): Promise<{ data: Record<string, any> }> =>
      axiosInstance.post('/api/market/fetch-batch', { sourceId, symbols }),
  },

  // Portfolio endpoints
  portfolio: {
    getHoldings: (): Promise<Holding[]> =>
      axiosInstance.get('/api/portfolio/holdings'),
    updateHoldings: (holdings: Partial<Holding>[]): Promise<Holding[]> =>
      axiosInstance.post('/api/portfolio/update', { holdings }),
    rebalance: (): Promise<TradeLog[]> =>
      axiosInstance.post('/api/portfolio/rebalance'),
    getDCASchedule: (): Promise<DCASchedule> =>
      axiosInstance.get('/api/portfolio/dca-schedule'),
    updateDCASchedule: (schedule: Partial<DCASchedule>): Promise<DCASchedule> =>
      axiosInstance.post('/api/portfolio/dca-schedule', schedule),
  },

  // Trading endpoints
  trading: {
    executeTrade: (trade: Partial<TradeLog>): Promise<TradeLog> =>
      axiosInstance.post('/api/trading/execute', trade),
    getTradeLogs: (filters?: any): Promise<TradeLog[]> =>
      axiosInstance.get('/api/trading/logs', { params: filters }),
    cancelOrder: (orderId: string): Promise<void> =>
      axiosInstance.post(`/api/trading/cancel/${orderId}`),
    exportTrades: (format: 'csv' | 'pdf'): Promise<Blob> =>
      axiosInstance.get('/api/trading/export', {
        params: { format },
        responseType: 'blob',
      }),
  },

  // Performance endpoints
  performance: {
    getMetrics: (): Promise<PerformanceMetrics> =>
      axiosInstance.get('/api/performance/metrics'),
    getDrawdownChart: (): Promise<any> =>
      axiosInstance.get('/api/performance/drawdown'),
    getReturnsChart: (period = '1Y'): Promise<any> =>
      axiosInstance.get('/api/performance/returns', { params: { period } }),
  },

  // Alert endpoints
  alerts: {
    getAlerts: (unreadOnly = false): Promise<Alert[]> =>
      axiosInstance.get('/api/alerts', { params: { unreadOnly } }),
    markAsRead: (alertId: string): Promise<void> =>
      axiosInstance.patch(`/api/alerts/${alertId}/read`),
    clearAll: (): Promise<void> =>
      axiosInstance.delete('/api/alerts'),
  },

  // Configuration endpoints
  config: {
    getSettings: (): Promise<Settings> =>
      axiosInstance.get('/api/config/settings'),
    updateSettings: (settings: Partial<Settings>): Promise<Settings> =>
      axiosInstance.post('/api/config/settings', settings),
    getPresets: (): Promise<ParameterPreset[]> =>
      axiosInstance.get('/api/config/presets'),
    saveCustomPreset: (preset: ParameterPreset): Promise<ParameterPreset> =>
      axiosInstance.post('/api/config/presets', preset),
  },

  // Health check
  health: {
    check: (): Promise<{ status: string; timestamp: string }> =>
      axiosInstance.get('/api/health'),
  },
};

export default api;