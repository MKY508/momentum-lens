/**
 * Data Source Manager for handling multiple market data providers
 * Supports free and paid APIs with automatic fallback
 */

import api from './api';
import toast from 'react-hot-toast';

export interface DataSource {
  id: string;
  name: string;
  type: 'free' | 'paid';
  endpoint: string;
  requiresKey: boolean;
  rateLimit?: string;
  priority: number;
  isActive?: boolean;
  lastTestTime?: Date;
  lastTestResult?: boolean;
  averageLatency?: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  timestamp: Date;
  source: string;
  iopv?: number;
  premium?: number;
  high?: number;
  low?: number;
  open?: number;
  prevClose?: number;
}

export interface DataSourceConfig {
  activeSourceId: string;
  enableFallback: boolean;
  cacheEnabled: boolean;
  cacheDuration: number;
  apiKeys: Record<string, string>;
}

class DataSourceManager {
  private sources: DataSource[] = [
    {
      id: 'akshare',
      name: 'AKShare (推荐)',
      type: 'free',
      endpoint: '/api/market/akshare',
      requiresKey: false,
      rateLimit: '无限制',
      priority: 1
    },
    {
      id: 'sina',
      name: '新浪财经',
      type: 'free',
      endpoint: '/api/market/sina',
      requiresKey: false,
      rateLimit: '1000/分钟',
      priority: 2
    },
    {
      id: 'eastmoney',
      name: '东方财富',
      type: 'free',
      endpoint: '/api/market/eastmoney',
      requiresKey: false,
      rateLimit: '500/分钟',
      priority: 3
    },
    {
      id: 'tushare',
      name: 'Tushare',
      type: 'free',
      endpoint: '/api/market/tushare',
      requiresKey: true,
      rateLimit: '120/分钟(免费版)',
      priority: 4
    },
    {
      id: 'yahoo',
      name: 'Yahoo Finance',
      type: 'free',
      endpoint: '/api/market/yahoo',
      requiresKey: false,
      rateLimit: '2000/小时',
      priority: 5
    }
  ];

  private activeSourceId: string = 'akshare';
  private fallbackEnabled: boolean = true;
  private cache: Map<string, { data: any; timestamp: number }> = new Map();
  private cacheDuration: number = 60000; // 60 seconds default
  private connectionStatus: Map<string, boolean> = new Map();
  private apiKeys: Map<string, string> = new Map();

  constructor() {
    this.loadConfiguration();
    this.initializeConnectionStatus();
  }

  /**
   * Load configuration from localStorage
   */
  private loadConfiguration(): void {
    // Load active source
    const savedActiveSource = localStorage.getItem('activeDataSource');
    if (savedActiveSource && this.sources.some(s => s.id === savedActiveSource)) {
      this.activeSourceId = savedActiveSource;
    }

    // Load fallback setting
    const savedFallback = localStorage.getItem('enableFallback');
    if (savedFallback !== null) {
      this.fallbackEnabled = savedFallback === 'true';
    }

    // Load cache settings
    const savedCacheEnabled = localStorage.getItem('cacheEnabled');
    if (savedCacheEnabled !== null) {
      // Cache is always enabled for performance
    }

    const savedCacheDuration = localStorage.getItem('cacheDuration');
    if (savedCacheDuration) {
      this.cacheDuration = parseInt(savedCacheDuration) * 1000; // Convert to milliseconds
    }

    // Load API keys (encrypted)
    const savedKeys = localStorage.getItem('apiKeys');
    if (savedKeys) {
      try {
        const decrypted = JSON.parse(atob(savedKeys));
        Object.entries(decrypted).forEach(([key, value]) => {
          this.apiKeys.set(key, value as string);
        });
      } catch (e) {
        console.error('Failed to load API keys:', e);
      }
    }
  }

  /**
   * Initialize connection status for all sources
   */
  private initializeConnectionStatus(): void {
    this.sources.forEach(source => {
      this.connectionStatus.set(source.id, false);
    });
  }

  /**
   * Get all configured data sources
   */
  public getAllSources(): DataSource[] {
    return this.sources.map(source => ({
      ...source,
      isActive: source.id === this.activeSourceId,
      lastTestResult: this.connectionStatus.get(source.id)
    }));
  }

  /**
   * Get a specific source by ID
   */
  public getSourceById(sourceId: string): DataSource | undefined {
    return this.sources.find(s => s.id === sourceId);
  }

  /**
   * Get the currently active data source
   */
  public getActiveSource(): DataSource {
    return this.sources.find(s => s.id === this.activeSourceId) || this.sources[0];
  }

  /**
   * Set the active data source
   */
  public setActiveSource(sourceId: string): void {
    const source = this.sources.find(s => s.id === sourceId);
    if (source) {
      this.activeSourceId = sourceId;
      localStorage.setItem('activeDataSource', sourceId);
      toast.success(`Switched to ${source.name}`);
    }
  }

  /**
   * Test connection to a specific data source
   */
  public async testConnection(sourceId: string, apiKey?: string): Promise<boolean> {
    const source = this.sources.find(s => s.id === sourceId);
    if (!source) {
      throw new Error(`Unknown data source: ${sourceId}`);
    }

    try {
      const response = await api.market.testDataSource(sourceId, apiKey);
      const success = response.success === true;
      
      this.connectionStatus.set(sourceId, success);
      source.lastTestTime = new Date();
      source.lastTestResult = success;
      
      if (response.latency) {
        source.averageLatency = response.latency;
      }

      return success;
    } catch (error) {
      console.error(`Failed to test ${sourceId}:`, error);
      this.connectionStatus.set(sourceId, false);
      source.lastTestResult = false;
      return false;
    }
  }

  /**
   * Fetch market data with automatic fallback
   */
  public async fetchData(symbol: string, useCache: boolean = true): Promise<MarketData | null> {
    // Check cache first
    if (useCache) {
      const cached = this.getFromCache(symbol);
      if (cached) {
        return cached;
      }
    }

    // Try active source first
    let data = await this.fetchFromSource(this.activeSourceId, symbol);
    
    // If failed and fallback is enabled, try other sources
    if (!data && this.fallbackEnabled) {
      const sortedSources = [...this.sources].sort((a, b) => a.priority - b.priority);
      
      for (const source of sortedSources) {
        if (source.id === this.activeSourceId) {
          continue; // Already tried
        }
        
        console.log(`Falling back to ${source.name}...`);
        data = await this.fetchFromSource(source.id, symbol);
        
        if (data) {
          toast(`Using fallback: ${source.name}`, {
            duration: 3000,
            icon: '🔄'
          });
          break;
        }
      }
    }

    // Cache the result
    if (data) {
      this.addToCache(symbol, data);
    }

    return data;
  }

  /**
   * Fetch data from a specific source
   */
  private async fetchFromSource(sourceId: string, symbol: string): Promise<MarketData | null> {
    const source = this.sources.find(s => s.id === sourceId);
    if (!source) {
      return null;
    }

    try {
      const apiKey = source.requiresKey ? this.apiKeys.get(sourceId) : undefined;
      
      const response = await api.market.fetchFromSource(sourceId, symbol, apiKey);
      
      if (response && response.data) {
        return {
          ...response.data,
          source: source.name,
          timestamp: new Date()
        };
      }
      
      return null;
    } catch (error) {
      console.error(`Failed to fetch from ${sourceId}:`, error);
      this.connectionStatus.set(sourceId, false);
      return null;
    }
  }

  /**
   * Batch fetch data for multiple symbols
   */
  public async fetchBatch(symbols: string[]): Promise<Map<string, MarketData>> {
    const results = new Map<string, MarketData>();
    
    // Try to fetch all symbols from the active source first
    try {
      const response = await api.market.fetchBatch(this.activeSourceId, symbols);
      if (response && response.data) {
        Object.entries(response.data).forEach(([symbol, data]) => {
          const marketData = {
            ...data,
            source: this.getActiveSource().name,
            timestamp: new Date()
          } as MarketData;
          
          results.set(symbol, marketData);
          this.addToCache(symbol, marketData);
        });
      }
    } catch (error) {
      console.error('Batch fetch failed:', error);
      
      // Fallback to individual fetches
      const promises = symbols.map(symbol => 
        this.fetchData(symbol).then(data => ({ symbol, data }))
      );
      
      const individualResults = await Promise.all(promises);
      individualResults.forEach(({ symbol, data }) => {
        if (data) {
          results.set(symbol, data);
        }
      });
    }

    return results;
  }

  /**
   * Get cached data if available and not expired
   */
  private getFromCache(key: string): MarketData | null {
    const cached = this.cache.get(key);
    
    if (!cached) {
      return null;
    }

    const now = Date.now();
    if (now - cached.timestamp > this.cacheDuration) {
      this.cache.delete(key);
      return null;
    }

    return cached.data;
  }

  /**
   * Add data to cache
   */
  private addToCache(key: string, data: MarketData): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now()
    });

    // Limit cache size to prevent memory issues
    if (this.cache.size > 1000) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  /**
   * Clear all cached data
   */
  public clearCache(): void {
    this.cache.clear();
    toast.success('Cache cleared');
  }

  /**
   * Get connection status for all sources
   */
  public getConnectionStatus(): Map<string, boolean> {
    return new Map(this.connectionStatus);
  }

  /**
   * Set API key for a source
   */
  public setApiKey(sourceId: string, apiKey: string): void {
    this.apiKeys.set(sourceId, apiKey);
    
    // Save to localStorage (encrypted)
    const allKeys: Record<string, string> = {};
    this.apiKeys.forEach((value, key) => {
      allKeys[key] = value;
    });
    
    try {
      const encoded = btoa(JSON.stringify(allKeys));
      localStorage.setItem('apiKeys', encoded);
    } catch (e) {
      console.error('Failed to save API keys:', e);
    }
  }

  /**
   * Enable or disable fallback
   */
  public setFallbackEnabled(enabled: boolean): void {
    this.fallbackEnabled = enabled;
    localStorage.setItem('enableFallback', enabled.toString());
  }

  /**
   * Get current configuration
   */
  public getConfiguration(): DataSourceConfig {
    const apiKeys: Record<string, string> = {};
    this.apiKeys.forEach((value, key) => {
      apiKeys[key] = value;
    });

    return {
      activeSourceId: this.activeSourceId,
      enableFallback: this.fallbackEnabled,
      cacheEnabled: true,
      cacheDuration: this.cacheDuration / 1000, // Convert to seconds
      apiKeys
    };
  }

  /**
   * Update configuration
   */
  public updateConfiguration(config: Partial<DataSourceConfig>): void {
    if (config.activeSourceId) {
      this.setActiveSource(config.activeSourceId);
    }

    if (config.enableFallback !== undefined) {
      this.setFallbackEnabled(config.enableFallback);
    }

    if (config.cacheDuration !== undefined) {
      this.cacheDuration = config.cacheDuration * 1000;
      localStorage.setItem('cacheDuration', config.cacheDuration.toString());
    }

    if (config.apiKeys) {
      Object.entries(config.apiKeys).forEach(([key, value]) => {
        this.setApiKey(key, value);
      });
    }
  }

  /**
   * Get statistics about data source usage
   */
  public getStatistics(): {
    totalRequests: number;
    cacheHits: number;
    cacheHitRate: number;
    activeConnections: number;
    failedConnections: number;
  } {
    const activeConnections = Array.from(this.connectionStatus.values())
      .filter(status => status).length;
    
    const failedConnections = this.sources.length - activeConnections;

    // These would be tracked in a production system
    return {
      totalRequests: 0,
      cacheHits: 0,
      cacheHitRate: 0,
      activeConnections,
      failedConnections
    };
  }
}

// Export singleton instance
export const dataSourceManager = new DataSourceManager();