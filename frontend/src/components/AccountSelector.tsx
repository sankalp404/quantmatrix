import React from 'react';
import {
  Box,
  Select,
  HStack,
  VStack,
  Text,
  Badge,
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Card,
  CardBody,
  Popover,
  PopoverTrigger,
  PopoverContent,
  PopoverBody,
  useColorModeValue,
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
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');

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
      <Select
        value={selectedAccount}
        onChange={(e) => onAccountChange(e.target.value)}
        size={size}
        maxW="250px"
      >
        {showAllOption && (
          <option value="all">All Accounts ({accounts.length})</option>
        )}
        {accounts.map(account => (
          <option key={account.account_id} value={account.account_id}>
            {account.account_name} - {formatCurrency(account.total_value)}
          </option>
        ))}
      </Select>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      {/* Account Selector */}
      <HStack spacing={4}>
        <Box>
          <Text fontSize="sm" fontWeight="medium" mb={2}>
            Portfolio View
          </Text>
          <Select
            value={selectedAccount}
            onChange={(e) => onAccountChange(e.target.value)}
            size={size}
            minW="300px"
            bg={bgColor}
            borderColor={borderColor}
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
          </Select>
        </Box>

        {/* Quick Info Popover */}
        <Popover trigger="hover" placement="bottom-start">
          <PopoverTrigger>
            <Box cursor="pointer" p={2} borderRadius="md" _hover={{ bg: hoverBg }}>
              <Icon as={FiInfo} color="gray.500" />
            </Box>
          </PopoverTrigger>
          <PopoverContent width="400px">
            <PopoverBody>
              <VStack spacing={3} align="stretch">
                <Text fontWeight="bold" fontSize="md">
                  {selectedAccount === 'all' ? 'Combined Portfolio' : selectedAccountData?.account_name}
                </Text>

                {selectedAccount === 'all' ? (
                  <SimpleGrid columns={2} spacing={4}>
                    <Stat size="sm">
                      <StatLabel>Total Value</StatLabel>
                      <StatNumber fontSize="md">{formatCurrency(totalValue)}</StatNumber>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Total P&L</StatLabel>
                      <StatNumber fontSize="md" color={getChangeColor(totalPnL)}>
                        <StatArrow type={totalPnL >= 0 ? 'increase' : 'decrease'} />
                        {formatCurrency(Math.abs(totalPnL))}
                      </StatNumber>
                      <StatHelpText>{formatPercentage(totalPnLPct)}</StatHelpText>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Accounts</StatLabel>
                      <StatNumber fontSize="md">{accounts.length}</StatNumber>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Total Positions</StatLabel>
                      <StatNumber fontSize="md">{totalPositions}</StatNumber>
                    </Stat>
                  </SimpleGrid>
                ) : selectedAccountData ? (
                  <SimpleGrid columns={2} spacing={4}>
                    <Stat size="sm">
                      <StatLabel>Account Value</StatLabel>
                      <StatNumber fontSize="md">{formatCurrency(selectedAccountData?.total_value || 0)}</StatNumber>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Unrealized P&L</StatLabel>
                      <StatNumber fontSize="md" color={getChangeColor(selectedAccountData?.unrealized_pnl)}>
                        <StatArrow type={(selectedAccountData?.unrealized_pnl || 0) >= 0 ? 'increase' : 'decrease'} />
                        {formatCurrency(Math.abs(selectedAccountData?.unrealized_pnl || 0))}
                      </StatNumber>
                      <StatHelpText>{formatPercentage(selectedAccountData.unrealized_pnl_pct)}</StatHelpText>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Positions</StatLabel>
                      <StatNumber fontSize="md">{selectedAccountData?.positions_count || 0}</StatNumber>
                    </Stat>
                    <Stat size="sm">
                      <StatLabel>Allocation</StatLabel>
                      <StatNumber fontSize="md">{((selectedAccountData?.allocation_pct ?? 0).toFixed(1))}%</StatNumber>
                    </Stat>
                    {(selectedAccountData?.buying_power != null) && (
                      <>
                        <Stat size="sm">
                          <StatLabel>Buying Power</StatLabel>
                          <StatNumber fontSize="md">{formatCurrency(selectedAccountData?.buying_power || 0)}</StatNumber>
                        </Stat>
                        <Stat size="sm">
                          <StatLabel>Available Funds</StatLabel>
                          <StatNumber fontSize="md">{formatCurrency(selectedAccountData.available_funds || 0)}</StatNumber>
                        </Stat>
                      </>
                    )}
                  </SimpleGrid>
                ) : null}

                <AppDivider />

                {/* Account Breakdown */}
                <VStack spacing={2} align="stretch">
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
        </Popover>
      </HStack>

      {/* Summary Cards (optional) */}
      {showSummary && (
        <Card bg={bgColor} borderColor={borderColor} size="sm">
          <CardBody>
            <SimpleGrid columns={{ base: 2, md: 4 }} spacing={4}>
              <Stat size="sm">
                <StatLabel>
                  <HStack>
                    <Icon as={FiDollarSign} />
                    <Text>Portfolio Value</Text>
                  </HStack>
                </StatLabel>
                <StatNumber>
                  {selectedAccount === 'all'
                    ? formatCurrency(totalValue)
                    : formatCurrency(selectedAccountData?.total_value || 0)
                  }
                </StatNumber>
              </Stat>

              <Stat size="sm">
                <StatLabel>
                  <HStack>
                    <Icon as={selectedAccount === 'all' ? (totalPnL >= 0 ? FiTrendingUp : FiTrendingDown) : (selectedAccountData?.unrealized_pnl || 0) >= 0 ? FiTrendingUp : FiTrendingDown} />
                    <Text>Unrealized P&L</Text>
                  </HStack>
                </StatLabel>
                <StatNumber color={getChangeColor(selectedAccount === 'all' ? totalPnL : selectedAccountData?.unrealized_pnl || 0)}>
                  <StatArrow type={(selectedAccount === 'all' ? totalPnL : selectedAccountData?.unrealized_pnl || 0) >= 0 ? 'increase' : 'decrease'} />
                  {formatCurrency(Math.abs(selectedAccount === 'all' ? totalPnL : selectedAccountData?.unrealized_pnl || 0))}
                </StatNumber>
                <StatHelpText>
                  {formatPercentage(selectedAccount === 'all' ? totalPnLPct : selectedAccountData?.unrealized_pnl_pct || 0)}
                </StatHelpText>
              </Stat>

              <Stat size="sm">
                <StatLabel>Positions</StatLabel>
                <StatNumber>
                  {selectedAccount === 'all' ? totalPositions : selectedAccountData?.positions_count || 0}
                </StatNumber>
                <StatHelpText>
                  {selectedAccount === 'all' ? `${accounts.length} accounts` : selectedAccountData?.account_type || ''}
                </StatHelpText>
              </Stat>

              <Stat size="sm">
                <StatLabel>Allocation</StatLabel>
                <StatNumber>
                  {selectedAccount === 'all' ? '100%' : `${(selectedAccountData?.allocation_pct ?? 0).toFixed(1)}%`}
                </StatNumber>
                <StatHelpText>
                  {selectedAccount === 'all' ? 'Combined' : `of total portfolio`}
                </StatHelpText>
              </Stat>
            </SimpleGrid>
          </CardBody>
        </Card>
      )}
    </VStack>
  );
};

export default AccountSelector; 