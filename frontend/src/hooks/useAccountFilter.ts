import { useState, useEffect, useMemo } from 'react';

export interface AccountData {
  account_id: string;
  account_name: string;
  account_type: string;
  broker: string;
  total_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  positions_count: number;
  allocation_pct: number;
  available_funds?: number;
  buying_power?: number;
  day_change?: number;
  day_change_pct?: number;
}

export interface FilterableItem {
  account?: string;
  account_id?: string;
  account_number?: string; // Add support for options data
  brokerage?: string;
  broker?: string;
  [key: string]: any;
}

export interface AccountFilterConfig {
  showAllOption?: boolean;
  defaultSelection?: string;
  filterByBrokerage?: boolean; // Whether to filter by brokerage name vs account ID
  size?: 'sm' | 'md' | 'lg';
  variant?: 'simple' | 'detailed';
  showSummary?: boolean;
}

export interface AccountFilterState {
  selectedAccount: string;
  setSelectedAccount: (accountId: string) => void;
  filteredData: FilterableItem[];
  accounts: AccountData[];
  totalValue: number;
  totalPnL: number;
  totalPositions: number;
  isLoading: boolean;
  error: string | null;
}

/**
 * Unified account filtering hook for consistent filtering across all pages
 * 
 * @param data - Array of items to filter (holdings, transactions, etc.)
 * @param accounts - Array of account data for the selector
 * @param config - Configuration options for the filter
 * @returns Filtered data and account selection state
 */
export const useAccountFilter = <T extends FilterableItem>(
  data: T[],
  accounts: AccountData[] = [],
  config: AccountFilterConfig = {}
): AccountFilterState => {
  const {
    showAllOption = true,
    defaultSelection = 'all',
    filterByBrokerage = false,
    size = 'md',
    variant = 'detailed',
    showSummary = true
  } = config;

  const [selectedAccount, setSelectedAccount] = useState<string>(defaultSelection);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter data based on selected account
  const filteredData = useMemo(() => {
    if (!data?.length) return [];

    if (selectedAccount === 'all') {
      return data;
    }

    return data.filter(item => {
      if (filterByBrokerage) {
        // Filter by brokerage name (IBKR, TASTYTRADE, etc.)
        return (
          item.brokerage?.toLowerCase() === selectedAccount.toLowerCase() ||
          item.broker?.toLowerCase() === selectedAccount.toLowerCase()
        );
      } else {
        // Filter by specific account ID (U19490886, etc.)
        return (
          item.account === selectedAccount ||
          item.account_id === selectedAccount ||
          item.account_number === selectedAccount
        );
      }
    });
  }, [data, selectedAccount, filterByBrokerage]);

  // Calculate aggregate metrics
  const { totalValue, totalPnL, totalPositions } = useMemo(() => {
    if (selectedAccount === 'all') {
      return {
        totalValue: accounts.reduce((sum, acc) => sum + acc.total_value, 0),
        totalPnL: accounts.reduce((sum, acc) => sum + acc.unrealized_pnl, 0),
        totalPositions: accounts.reduce((sum, acc) => sum + acc.positions_count, 0),
      };
    } else {
      const selectedAccountData = accounts.find(acc => acc.account_id === selectedAccount);
      return {
        totalValue: selectedAccountData?.total_value || 0,
        totalPnL: selectedAccountData?.unrealized_pnl || 0,
        totalPositions: selectedAccountData?.positions_count || 0,
      };
    }
  }, [accounts, selectedAccount]);

  // Reset selection if accounts change and current selection is invalid
  useEffect(() => {
    if (accounts.length > 0 && selectedAccount !== 'all') {
      const accountExists = accounts.some(acc => acc.account_id === selectedAccount);
      if (!accountExists) {
        setSelectedAccount(defaultSelection);
      }
    }
  }, [accounts, selectedAccount, defaultSelection]);

  return {
    selectedAccount,
    setSelectedAccount,
    filteredData,
    accounts,
    totalValue,
    totalPnL,
    totalPositions,
    isLoading,
    error,
  };
};

/**
 * Helper function to transform portfolio data into AccountData format
 * for use with the account filter
 */
export const transformPortfolioToAccounts = (portfolioData: any): AccountData[] => {
  if (!portfolioData?.accounts) return [];

  return Object.entries(portfolioData.accounts).map(([accountId, accountData]: [string, any]) => ({
    account_id: accountId,
    account_name: accountData.account_summary?.account_name || `Account ${accountId}`,
    account_type: accountData.account_summary?.account_type || 'taxable',
    broker: accountData.account_summary?.broker || 'IBKR',
    total_value: accountData.account_summary?.net_liquidation || 0,
    unrealized_pnl: accountData.account_summary?.unrealized_pnl || 0,
    unrealized_pnl_pct: accountData.account_summary?.unrealized_pnl_pct || 0,
    positions_count: accountData.all_positions?.length || 0,
    allocation_pct: 0, // Calculate this based on total portfolio
    available_funds: accountData.account_summary?.available_funds,
    buying_power: accountData.account_summary?.buying_power,
    day_change: accountData.account_summary?.day_change,
    day_change_pct: accountData.account_summary?.day_change_pct,
  }));
};

/**
 * Helper function to get formatted account display name
 */
export const getAccountDisplayName = (account: AccountData): string => {
  const value = account.total_value;
  const pnlPct = account.unrealized_pnl_pct;
  const formattedValue = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);

  const formattedPnL = `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%`;

  return `${account.account_name} • ${formattedValue} • ${formattedPnL}`;
};

export default useAccountFilter; 