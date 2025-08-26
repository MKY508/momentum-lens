import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Add auth token if exists
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Market APIs
export const marketAPI = {
  getEnvironment: () => api.get('/api/market/environment'),
}

// Decision APIs
export const decisionAPI = {
  generate: () => api.post('/api/decisions/generate'),
  getSatelliteSelections: (topN: number = 2) => 
    api.get(`/api/decisions/satellite?top_n=${topN}`),
}

// Portfolio APIs
export const portfolioAPI = {
  getSummary: () => api.get('/api/portfolio/summary'),
  getPositions: () => api.get('/api/portfolio/positions'),
  updatePrices: (prices: Record<string, number>) => 
    api.post('/api/portfolio/update-prices', { prices }),
  generateRebalance: (threshold: number = 0.02, dryRun: boolean = true) =>
    api.post('/api/portfolio/rebalance', { threshold, dry_run: dryRun }),
  executeDCA: (week: number) => 
    api.post('/api/portfolio/dca', { week }),
  checkRisks: () => api.get('/api/portfolio/risks'),
}

// Data APIs
export const dataAPI = {
  getETFList: (minTurnover: number = 50_000_000) =>
    api.get(`/api/data/etfs?min_turnover=${minTurnover}`),
  getETFPrice: (code: string, days: number = 30) =>
    api.get(`/api/data/etf/${code}/price?days=${days}`),
  getETFIOPV: (code: string) =>
    api.get(`/api/data/etf/${code}/iopv`),
  getConvertibles: () =>
    api.get('/api/data/convertibles'),
}

// Momentum APIs
export const momentumAPI = {
  getRanking: (topN: number = 20) =>
    api.get(`/api/momentum/ranking?top_n=${topN}`),
}

// Export APIs
export const exportAPI = {
  downloadOrdersCSV: () => {
    window.open(`${API_BASE_URL}/api/export/orders/csv`, '_blank')
  },
}

export default api