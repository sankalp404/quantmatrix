import React, { ReactNode } from 'react';
import { Box, VStack, Alert, AlertIcon, Spinner, Text } from '@chakra-ui/react';
import AccountSelector from './AccountSelector';
import { useAccountFilter, AccountData, FilterableItem, AccountFilterConfig } from '../hooks/useAccountFilter';

interface AccountFilterWrapperProps<T extends FilterableItem> {
  data: T[];
  accounts: AccountData[];
  config?: AccountFilterConfig;
  loading?: boolean;
  error?: string | null;
  onAccountChange?: (accountId: string) => void;
  children: (filteredData: T[], filterState: ReturnType<typeof useAccountFilter>) => ReactNode;
}

/**
 * Reusable wrapper component that provides consistent account filtering UI and logic
 * across all pages in the application.
 * 
 * Usage:
 * <AccountFilterWrapper data={holdings} accounts={accounts}>
 *   {(filteredData, filterState) => (
 *     // Your page content with filtered data
 *   )}
 * </AccountFilterWrapper>
 */
function AccountFilterWrapper<T extends FilterableItem>({
  data,
  accounts,
  config = {},
  loading = false,
  error = null,
  onAccountChange,
  children,
}: AccountFilterWrapperProps<T>) {
  const filterState = useAccountFilter(data, accounts, config);

  // Handle account selection changes
  const handleAccountChange = (accountId: string) => {
    filterState.setSelectedAccount(accountId);
    onAccountChange?.(accountId);
  };

  // Show loading state
  if (loading) {
    return (
      <VStack spacing={4} py={8}>
        <Spinner size="xl" color="blue.500" />
        <Text>Loading account data...</Text>
      </VStack>
    );
  }

  // Show error state
  if (error) {
    return (
      <Alert status="error" borderRadius="md">
        <AlertIcon />
        Error loading account data: {error}
      </Alert>
    );
  }

  return (
    <VStack spacing={6} align="stretch">
      {/* Account Filter UI */}
      <AccountSelector
        accounts={accounts}
        selectedAccount={filterState.selectedAccount}
        onAccountChange={handleAccountChange}
        showAllOption={config.showAllOption}
        showSummary={config.showSummary}
        size={config.size}
        variant={config.variant}
      />

      {/* Page Content with Filtered Data */}
      <Box>
        {children(filterState.filteredData as T[], filterState)}
      </Box>
    </VStack>
  );
}

export default AccountFilterWrapper; 