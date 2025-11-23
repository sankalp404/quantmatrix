import { useQuery, useMutation, useQueryClient } from 'react-query';
import { portfolioApi, tasksApi, handleApiError, PortfolioSummary, accountsApi } from '../services/api';
import toast from 'react-hot-toast';

// Main hook for live portfolio data (used by most components)
export const usePortfolio = () => {
  return useQuery(
    'livePortfolio',
    async () => {
      // Use the centralized portfolioApi instead of direct fetch
      const result = await portfolioApi.getLive();
      return result.data; // Extract the data portion from the API response
    },
    {
      refetchInterval: 30000, // Refetch every 30 seconds for live data
      staleTime: 20000, // Consider data stale after 20 seconds
      onError: (error) => {
        console.error('Portfolio data fetch failed:', error);
        toast.error('Failed to load portfolio data');
      },
    }
  );
};

// Hook for portfolio summary data
export const usePortfolioSummary = (accountId?: string) => {
  return useQuery(
    ['portfolioSummary', accountId],
    () => portfolioApi.getDashboard(accountId),
    {
      refetchInterval: 30000, // Refetch every 30 seconds
      staleTime: 20000, // Consider data stale after 20 seconds
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`Portfolio Error: ${message}`);
      },
    }
  );
};

// Hook for portfolio health check
export const usePortfolioHealth = () => {
  return useQuery(
    'portfolioHealth',
    () => portfolioApi.getDashboard(),
    {
      refetchInterval: 60000, // Check every minute
      staleTime: 30000,
      onError: (error) => {
        const message = handleApiError(error);
        console.error('Portfolio health check failed:', message);
      },
    }
  );
};

// Hook for portfolio accounts
export const usePortfolioAccounts = () => {
  return useQuery(
    'portfolioAccounts',
    accountsApi.list,
    {
      staleTime: 300000, // 5 minutes
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`Accounts Error: ${message}`);
      },
    }
  );
};

// Hook for syncing portfolio data
export const usePortfolioSync = () => {
  const queryClient = useQueryClient();

  return useMutation(
    portfolioApi.sync,
    {
      onMutate: () => {
        toast.loading('Syncing portfolio data...', { id: 'portfolio-sync' });
      },
      onSuccess: (data) => {
        // Invalidate and refetch portfolio queries
        queryClient.invalidateQueries('portfolioSummary');
        queryClient.invalidateQueries('portfolioHealth');
        toast.success('Portfolio data synced successfully', { id: 'portfolio-sync' });
      },
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`Sync failed: ${message}`, { id: 'portfolio-sync' });
      },
    }
  );
};

// Hook for sending portfolio digest
export const usePortfolioDigest = () => {
  return useMutation(
    tasksApi.sendPortfolioDigest,
    {
      onMutate: () => {
        toast.loading('Sending portfolio digest...', { id: 'portfolio-digest' });
      },
      onSuccess: (data) => {
        toast.success('Portfolio digest sent to Discord', { id: 'portfolio-digest' });
      },
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`Failed to send digest: ${message}`, { id: 'portfolio-digest' });
      },
    }
  );
};

// Hook for forcing portfolio alerts
export const usePortfolioAlerts = () => {
  return useMutation(
    tasksApi.forcePortfolioAlerts,
    {
      onMutate: () => {
        toast.loading('Generating portfolio alerts...', { id: 'portfolio-alerts' });
      },
      onSuccess: (data) => {
        toast.success(`Generated ${data.alerts_generated || 0} portfolio alerts`, { id: 'portfolio-alerts' });
      },
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`Failed to generate alerts: ${message}`, { id: 'portfolio-alerts' });
      },
    }
  );
};

// Hook for sending signals
export const useSignals = () => {
  return useMutation(
    tasksApi.sendSignals,
    {
      onMutate: () => {
        toast.loading('Generating trading signals...', { id: 'signals' });
      },
      onSuccess: (data) => {
        toast.success('Trading signals sent to Discord', { id: 'signals' });
      },
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`Failed to send signals: ${message}`, { id: 'signals' });
      },
    }
  );
};

// Hook for sending morning brew
export const useMorningBrew = () => {
  return useMutation(
    tasksApi.sendMorningBrew,
    {
      onMutate: () => {
        toast.loading('Preparing morning brew...', { id: 'morning-brew' });
      },
      onSuccess: (data) => {
        toast.success('Morning brew sent to Discord', { id: 'morning-brew' });
      },
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`Failed to send morning brew: ${message}`, { id: 'morning-brew' });
      },
    }
  );
};

// Hook for system status
export const useSystemStatus = () => {
  return useMutation(
    tasksApi.sendSystemStatus,
    {
      onMutate: () => {
        toast.loading('Checking system status...', { id: 'system-status' });
      },
      onSuccess: (data) => {
        toast.success('System status sent to Discord', { id: 'system-status' });
      },
      onError: (error) => {
        const message = handleApiError(error);
        toast.error(`System status check failed: ${message}`, { id: 'system-status' });
      },
    }
  );
};

// Combined hook for dashboard data
export const useDashboardData = () => {
  const portfolioSummary = usePortfolioSummary();
  const portfolioHealth = usePortfolioHealth();
  const portfolioAccounts = usePortfolioAccounts();

  return {
    portfolio: portfolioSummary,
    health: portfolioHealth,
    accounts: portfolioAccounts,
    isLoading: portfolioSummary.isLoading || portfolioHealth.isLoading,
    isError: portfolioSummary.isError || portfolioHealth.isError,
    error: portfolioSummary.error || portfolioHealth.error,
  };
};

// Helper function to transform API data for charts
export const transformPortfolioDataForCharts = (data: PortfolioSummary) => {
  const anyData: any = data as any;
  const positions = anyData?.all_positions || anyData?.positions || [];
  return positions.map((position: any) => ({
    symbol: position.symbol,
    value: position.market_value ?? position.value ?? 0,
    gainLoss: position.unrealized_pnl ?? 0,
    gainLossPct: position.unrealized_pnl_pct ?? 0,
    account: position.account,
  }));
}; 