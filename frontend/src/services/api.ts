/// <reference types="vite/client" />
import axios, { AxiosResponse, AxiosError } from 'axios';

// Use import.meta.env for Vite compatibility
const API_BASE_URL = import.meta.env.MODE === 'production' ? '/api/v1' : 'http://localhost:8000/api/v1';

// Enhanced request queue for connection optimization
class RequestQueue {
  private queue: Array<() => Promise<any>> = [];
  private processing = false;
  private maxConcurrent = 6; // Optimize for backend connection limits
  private activeRequests = 0;

  async add<T>(requestFn: () => Promise<T>): Promise<T> {
    return new Promise((resolve, reject) => {
      this.queue.push(async () => {
        try {
          this.activeRequests++;
          const result = await requestFn();
          resolve(result);
        } catch (error) {
          reject(error);
        } finally {
          this.activeRequests--;
          this.processNext();
        }
      });
      this.processNext();
    });
  }

  private processNext() {
    if (this.activeRequests >= this.maxConcurrent || this.queue.length === 0) {
      return;
    }

    const nextRequest = this.queue.shift();
    if (nextRequest) {
      nextRequest();
    }
  }
}

const requestQueue = new RequestQueue();

// Enhanced axios instance with optimization
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // Reduced timeout for faster feedback
  // Connection optimization
  maxRedirects: 3,
});

// Enhanced request interceptor with queue and retry logic
api.interceptors.request.use(
  (config) => {
    console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);

    // Add cache headers for GET requests
    if (config.method === 'get') {
      config.headers['Cache-Control'] = 'max-age=30';
    }

    return config;
  },
  (error) => {
    console.error('❌ Request Error:', error);
    return Promise.reject(error);
  }
);

// Enhanced response interceptor with better error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.config.url} - ${response.status} (${response.headers['x-response-time'] || 'unknown'}ms)`);
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // Enhanced error logging
    console.error('❌ Response Error:', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
      data: error.response?.data
    });

    // Retry logic for network errors
    if ((error.code === 'ECONNABORTED' || error.code === 'ERR_NETWORK') && originalRequest) {
      if (!(originalRequest as any)._retry) {
        (originalRequest as any)._retry = true;
        console.log('🔄 Retrying request:', originalRequest.url);
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1s before retry
        return api(originalRequest);
      }
    }

    return Promise.reject(error);
  }
);

// Optimized API call wrapper with queue
const makeOptimizedRequest = async <T>(requestFn: () => Promise<AxiosResponse<T>>) => {
  return requestQueue.add(async () => {
    const response = await requestFn();
    return response.data;
  });
};

// Portfolio API endpoints - enhanced with optimization
export const portfolioApi = {
  getLive: async (accountId?: string) => {
    const url = accountId ? `/portfolio/live?account_id=${encodeURIComponent(accountId)}` : '/portfolio/live';
    return makeOptimizedRequest(() => api.get(url));
  },

  getDashboard: async (brokerage?: string) => {
    const url = brokerage ? `/portfolio/dashboard?brokerage=${brokerage}` : '/portfolio/dashboard';
    return makeOptimizedRequest(() => api.get(url));
  },

  sync: async (brokerage?: string) => {
    return makeOptimizedRequest(() => api.post('/portfolio/sync', { brokerage }));
  },

  getTaxLots: async () => {
    return makeOptimizedRequest(() => api.get('/portfolio/tax-lots'));
  },

  getHoldingTaxLots: async (holdingId: number) => {
    return makeOptimizedRequest(() => api.get(`/portfolio/holdings/${holdingId}/tax-lots`));
  },

  getStocksOnly: async (accountId?: string) => {
    const url = accountId ? `/portfolio/holdings/stocks-only?account_id=${encodeURIComponent(accountId)}` : '/portfolio/holdings/stocks-only';
    return makeOptimizedRequest(() => api.get(url));
  },

  // Enhanced statements with error handling
  getStatements: async (accountId?: string, days: number = 30) => {
    const url = accountId ? `/portfolio/statements?account_id=${encodeURIComponent(accountId)}&days=${days}` : `/portfolio/statements?days=${days}`;
    try {
      return await makeOptimizedRequest(() => api.get(url));
    } catch (error) {
      console.warn('Statements API fallback to sample data');
      return {
        status: 'success',
        data: {
          transactions: [],
          summary: { total_transactions: 0 },
          message: 'IBKR connection unavailable - using sample data'
        }
      };
    }
  },

  // Enhanced dividends with fallback
  getDividends: async (accountId?: string, days: number = 365) => {
    const url = accountId ? `/portfolio/dividends?days=${days}&account_id=${encodeURIComponent(accountId)}` : `/portfolio/dividends?days=${days}`;
    try {
      return await makeOptimizedRequest(() => api.get(url));
    } catch (error) {
      console.warn('Dividends API fallback');
      return {
        status: 'success',
        data: {
          dividends: [],
          summary: {},
          message: 'Dividend data unavailable'
        }
      };
    }
  },

  // Batch API calls for improved performance
  getBatchData: async (endpoints: string[]) => {
    try {
      const requests = endpoints.map(endpoint => api.get(endpoint));
      const responses = await Promise.allSettled(requests);

      return responses.map((response, index) => ({
        endpoint: endpoints[index],
        success: response.status === 'fulfilled',
        data: response.status === 'fulfilled' ? response.value.data : null,
        error: response.status === 'rejected' ? response.reason : null
      }));
    } catch (error) {
      console.error('Batch API call failed:', error);
      throw error;
    }
  }
};

// Options API endpoints - enhanced
export const optionsApi = {
  getPortfolio: async () => {
    return makeOptimizedRequest(() => api.get('/options/unified/portfolio'));
  },

  getSummary: async () => {
    return makeOptimizedRequest(() => api.get('/options/unified/summary'));
  },

  sync: async () => {
    return makeOptimizedRequest(() => api.post('/options/unified/sync'));
  },

  // Batch options data
  getBatchOptionsData: async () => {
    return portfolioApi.getBatchData([
      '/options/unified/portfolio',
      '/options/unified/summary'
    ]);
  }
};

// TastyTrade API endpoints - enhanced
export const tastytradeApi = {
  getAccounts: async () => {
    try {
      return await makeOptimizedRequest(() => api.get('/tastytrade/accounts'));
    } catch (error) {
      console.warn('TastyTrade API not available');
      return { status: 'error', message: 'TastyTrade API unavailable' };
    }
  },

  sync: async () => {
    return makeOptimizedRequest(() => api.post('/tastytrade/portfolio/sync'));
  }
};

// Tasks API endpoints - for Discord notifications and alerts
export const tasksApi = {
  sendPortfolioDigest: async () => {
    return makeOptimizedRequest(() => api.post('/tasks/portfolio-digest'));
  },

  forcePortfolioAlerts: async () => {
    return makeOptimizedRequest(() => api.post('/tasks/portfolio-alerts'));
  },

  sendSignals: async () => {
    return makeOptimizedRequest(() => api.post('/tasks/signals'));
  },

  sendMorningBrew: async () => {
    return makeOptimizedRequest(() => api.post('/tasks/morning-brew'));
  },

  sendSystemStatus: async () => {
    return makeOptimizedRequest(() => api.post('/tasks/system-status'));
  }
};

// Enhanced error handler with user-friendly messages
export const handleApiError = (error: any): string => {
  // Enhanced network error detection
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
    return 'Connection failed - check if backend is running on port 8000';
  }

  if (error.response) {
    const status = error.response.status;
    const message = error.response.data?.detail || error.response.data?.message || 'Unknown error';

    switch (status) {
      case 503:
        return 'Service unavailable - IBKR connection required';
      case 500:
        return 'Server error - check backend logs';
      case 502:
        return 'Bad gateway - backend service may be restarting';
      case 504:
        return 'Request timeout - try again in a moment';
      case 404:
        return 'Endpoint not found';
      case 429:
        return 'Too many requests - please wait a moment';
      default:
        return `Error ${status}: ${message}`;
    }
  } else if (error.request) {
    return 'No response from server - backend may be offline';
  } else {
    return error.message || 'Request failed';
  }
};

// Connection health checker
export const checkBackendHealth = async (): Promise<boolean> => {
  try {
    await api.get('/health', { timeout: 5000 });
    return true;
  } catch (error) {
    console.warn('Backend health check failed:', error);
    return false;
  }
};

// Performance monitoring
export const getApiPerformanceMetrics = () => {
  return {
    activeRequests: (requestQueue as any).activeRequests,
    queueLength: (requestQueue as any).queue.length,
    maxConcurrent: (requestQueue as any).maxConcurrent
  };
};

// Export types
export interface PortfolioSummary {
  total_value: number;
  total_unrealized_pnl: number;
  total_unrealized_pnl_pct: number;
  accounts_summary: any[];
}

export default api; 