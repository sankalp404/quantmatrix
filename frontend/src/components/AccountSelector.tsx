import React from 'react';
import {
  Box,
  HStack,
  VStack,
  Text,
  Badge,
  StatRoot,
  StatLabel,
  StatHelpText,
  StatValueText,
  StatUpIndicator,
  StatDownIndicator,
  CardRoot,
  CardBody,
  PopoverRoot,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  Icon,
  Flex,
  SimpleGrid
} from '@chakra-ui/react';
import { FiInfo, FiTrendingUp, FiTrendingDown, FiDollarSign } from 'react-icons/fi';
import AppDivider from './ui/AppDivider';

interface AccountData {
  account_id: string;
  account_name: string;
  account_type: string;
  broker: string;
  total_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct?: number; // Make optional to handle missing data
  positions_count: number;
  allocation_pct: number;
  available_funds?: number;
  buying_power?: number;
  day_change?: number;
  day_change_pct?: number;
}

interface AccountSelectorProps {
  accounts: AccountData[];
  selectedAccount: string;
  onAccountChange: (accountId: string) => void;
  showAllOption?: boolean;
  showSummary?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'simple' | 'detailed';
}

const AccountSelector: React.FC<AccountSelectorProps> = ({
  accounts = [],
  selectedAccount,
  onAccountChange,
  showAllOption = true,
  showSummary = true,
  size = 'md',
  variant = 'detailed'
}) => {
  const bgColor = 'bg.card';
  const borderColor = 'border.subtle';
  const hoverBg = 'bg.panel';

  // Calculate totals
  const totalValue = accounts.reduce((sum, acc) => sum + acc.total_value, 0);
  const totalPnL = accounts.reduce((sum, acc) => sum + acc.unrealized_pnl, 0);
  const totalPnLPct = totalValue > 0 ? (totalPnL / (totalValue - totalPnL)) * 100 : 0;
  const totalPositions = accounts.reduce((sum, acc) => sum + acc.positions_count, 0);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const formatPercentage = (pct: number | undefined) => {
    if (pct === undefined || pct === null || isNaN(pct)) return '0.00%';
    return `${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
  };

  const getChangeColor = (value: number | undefined) => {
    if (value === undefined || value === null || isNaN(value)) return 'gray.500';
    return value >= 0 ? 'green.500' : 'red.500';
  };

  const selectedAccountData = accounts.find(acc => acc.account_id === selectedAccount);

  if (variant === 'simple') {
    return (
      <select
        value={selectedAccount}
        onChange={(e: React.ChangeEvent<HTMLSelectElement>) => onAccountChange(e.target.value)}
        disabled={!accounts.length}
        style={{
          maxWidth: 250,
          padding: '8px 10px',
          borderRadius: 10,
          border: '1px solid #e5e7eb',
          background: 'white',
          fontSize: 14,
        }}
      >
        {showAllOption && (
          <option value="all">All Accounts ({accounts.length})</option>
        )}
        {accounts.map(account => (
          <option key={account.account_id} value={account.account_id}>
            {account.account_name} - {formatCurrency(account.total_value)}
          </option>
        ))}
      </select>
    );
  }

  return (
    <VStack gap={4} align="stretch">
      {/* Account Selector */}
      <HStack gap={4}>
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Portfolio View
          </Text>
          <select
            value={selectedAccount}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) => onAccountChange(e.target.value)}
            disabled={!accounts.length}
            style={{
              minWidth: 300,
              padding: '8px 10px',
              borderRadius: 10,
              border: `1px solid ${String(borderColor)}`,
              background: String(bgColor),
              fontSize: 14,
            }}
          >
            {showAllOption && (
              <option value="all">
                Combined Portfolio • {formatCurrency(totalValue)} • {formatPercentage(totalPnLPct)}
              </option>
            )}
            {accounts.map(account => (
              <option key={account.account_id} value={account.account_id}>
                {account.account_name} • {formatCurrency(account.total_value)} • {formatPercentage(account.unrealized_pnl_pct)}
              </option>
            ))}
          </select>
        </Box>

        {/* Quick Info Popover */}
        <PopoverRoot positioning={{ placement: 'bottom-start' }}>
          <PopoverTrigger asChild>
            <Box cursor="pointer" p={2} borderRadius="md" _hover={{ bg: hoverBg }}>
              <Icon as={FiInfo} color="gray.500" />
            </Box>
          </PopoverTrigger>
          <PopoverContent width="400px">
            <PopoverBody>
              <VStack gap={3} align="stretch">
                <Text fontWeight="bold" fontSize="md">
                  {selectedAccount === 'all' ? 'Combined Portfolio' : selectedAccountData?.account_name}
                </Text>

                {selectedAccount === 'all' ? (
                  <SimpleGrid columns={2} gap={4}>
                    <StatRoot size="sm">
                      <StatLabel>Total Value</StatLabel>
                      <StatValueText fontSize="md">{formatCurrency(totalValue)}</StatValueText>
                    </StatRoot>
                    <StatRoot size="sm">
                      <StatLabel>Total P&L</StatLabel>
                      <StatValueText fontSize="md" color={getChangeColor(totalPnL)}>
                        {totalPnL >= 0 ? <StatUpIndicator /> : <StatDownIndicator />}
                        {formatCurrency(Math.abs(totalPnL))}
                      </StatValueText>
                      <StatHelpText>{formatPercentage(totalPnLPct)}</StatHelpText>
                    </StatRoot>
                    <StatRoot size="sm">
                      <StatLabel>Accounts</StatLabel>
                      <StatValueText fontSize="md">{accounts.length}</StatValueText>
                    </StatRoot>
                    <StatRoot size="sm">
                      <StatLabel>Total Positions</StatLabel>
                      <StatValueText fontSize="md">{totalPositions}</StatValueText>
                    </StatRoot>
                  </SimpleGrid>
                ) : selectedAccountData ? (
                  <SimpleGrid columns={2} gap={4}>
                    <StatRoot size="sm">
                      <StatLabel>Account Value</StatLabel>
                      <StatValueText fontSize="md">{formatCurrency(selectedAccountData?.total_value || 0)}</StatValueText>
                    </StatRoot>
                    <StatRoot size="sm">
                      <StatLabel>Unrealized P&L</StatLabel>
                      <StatValueText fontSize="md" color={getChangeColor(selectedAccountData?.unrealized_pnl)}>
                        {(selectedAccountData?.unrealized_pnl || 0) >= 0 ? <StatUpIndicator /> : <StatDownIndicator />}
                        {formatCurrency(Math.abs(selectedAccountData?.unrealized_pnl || 0))}
                      </StatValueText>
                      <StatHelpText>{formatPercentage(selectedAccountData.unrealized_pnl_pct)}</StatHelpText>
                    </StatRoot>
                    <StatRoot size="sm">
                      <StatLabel>Positions</StatLabel>
                      <StatValueText fontSize="md">{selectedAccountData?.positions_count || 0}</StatValueText>
                    </StatRoot>
                    <StatRoot size="sm">
                      <StatLabel>Allocation</StatLabel>
                      <StatValueText fontSize="md">{((selectedAccountData?.allocation_pct ?? 0).toFixed(1))}%</StatValueText>
                    </StatRoot>
                    {(selectedAccountData?.buying_power != null) && (
                      <>
                        <StatRoot size="sm">
                          <StatLabel>Buying Power</StatLabel>
                          <StatValueText fontSize="md">{formatCurrency(selectedAccountData?.buying_power || 0)}</StatValueText>
                        </StatRoot>
                        <StatRoot size="sm">
                          <StatLabel>Available Funds</StatLabel>
                          <StatValueText fontSize="md">{formatCurrency(selectedAccountData.available_funds || 0)}</StatValueText>
                        </StatRoot>
                      </>
                    )}
                  </SimpleGrid>
                ) : null}

                <AppDivider />

                {/* Account Breakdown */}
                <VStack gap={2} align="stretch">
                  <Text fontSize="sm" fontWeight="medium">Account Breakdown:</Text>
                  {accounts.map((account, index) => (
                    <HStack key={`${account.account_id}-${index}`} justify="space-between" fontSize="sm">
                      <HStack>
                        <Badge size="sm" colorScheme={account.broker === 'IBKR' ? 'blue' : 'orange'}>
                          {account.broker}
                        </Badge>
                        <Text>{account.account_name}</Text>
                      </HStack>
                      <HStack>
                        <Text>{formatCurrency(account.total_value)}</Text>
                        <Text color={getChangeColor(account.unrealized_pnl)}>
                          ({formatPercentage(account.unrealized_pnl_pct)})
                        </Text>
                      </HStack>
                    </HStack>
                  ))}
                </VStack>
              </VStack>
            </PopoverBody>
          </PopoverContent>
        </PopoverRoot>
      </HStack>

      {/* Summary Cards (optional) */}
      {showSummary && (
        <CardRoot bg={bgColor} borderColor={borderColor} borderWidth="1px" borderRadius="xl">
          <CardBody>
            <SimpleGrid columns={{ base: 2, md: 4 }} gap={4}>
              <StatRoot size="sm">
                <StatLabel>
                  <HStack gap={1}>
                    <Icon as={FiDollarSign} />
                    <Text>Portfolio Value</Text>
                  </HStack>
                </StatLabel>
                <StatValueText>
                  {selectedAccount === 'all'
                    ? formatCurrency(totalValue)
                    : formatCurrency(selectedAccountData?.total_value || 0)
                  }
                </StatValueText>
              </StatRoot>

              <StatRoot size="sm">
                <StatLabel>
                  <HStack gap={1}>
                    <Icon as={selectedAccount === 'all' ? (totalPnL >= 0 ? FiTrendingUp : FiTrendingDown) : (selectedAccountData?.unrealized_pnl || 0) >= 0 ? FiTrendingUp : FiTrendingDown} />
                    <Text>Unrealized P&L</Text>
                  </HStack>
                </StatLabel>
                <StatValueText color={getChangeColor(selectedAccount === 'all' ? totalPnL : selectedAccountData?.unrealized_pnl || 0)}>
                  {(selectedAccount === 'all' ? totalPnL : selectedAccountData?.unrealized_pnl || 0) >= 0 ? <StatUpIndicator /> : <StatDownIndicator />}
                  {formatCurrency(Math.abs(selectedAccount === 'all' ? totalPnL : selectedAccountData?.unrealized_pnl || 0))}
                </StatValueText>
                <StatHelpText>
                  {formatPercentage(selectedAccount === 'all' ? totalPnLPct : selectedAccountData?.unrealized_pnl_pct || 0)}
                </StatHelpText>
              </StatRoot>

              <StatRoot size="sm">
                <StatLabel>Positions</StatLabel>
                <StatValueText>
                  {selectedAccount === 'all' ? totalPositions : selectedAccountData?.positions_count || 0}
                </StatValueText>
                <StatHelpText>
                  {selectedAccount === 'all' ? `${accounts.length} accounts` : selectedAccountData?.account_type || ''}
                </StatHelpText>
              </StatRoot>

              <StatRoot size="sm">
                <StatLabel>Allocation</StatLabel>
                <StatValueText>
                  {selectedAccount === 'all' ? '100%' : `${(selectedAccountData?.allocation_pct ?? 0).toFixed(1)}%`}
                </StatValueText>
                <StatHelpText>
                  {selectedAccount === 'all' ? 'Combined' : `of total portfolio`}
                </StatHelpText>
              </StatRoot>
            </SimpleGrid>
          </CardBody>
        </CardRoot>
      )}
    </VStack>
  );
};

export default AccountSelector; 