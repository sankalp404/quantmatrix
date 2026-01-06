import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { useColorMode } from '../theme/colorMode';
import AccountSelector, { type AccountData } from '../components/ui/AccountSelector';
import AccountFilterWrapper from '../components/ui/AccountFilterWrapper';

export default {
  title: 'DesignSystem/Accounts',
};

const accounts: AccountData[] = [
  {
    account_id: 'A1',
    account_name: 'Taxable',
    account_type: 'taxable',
    broker: 'tastytrade',
    total_value: 125_450,
    unrealized_pnl: 3_120,
    unrealized_pnl_pct: 2.6,
    positions_count: 34,
    allocation_pct: 70,
    buying_power: 45_000,
    available_funds: 12_400,
    day_change: 820,
    day_change_pct: 0.7,
  },
  {
    account_id: 'A2',
    account_name: 'IRA',
    account_type: 'ira',
    broker: 'ibkr',
    total_value: 53_900,
    unrealized_pnl: -540,
    unrealized_pnl_pct: -1.0,
    positions_count: 12,
    allocation_pct: 30,
    buying_power: 9_500,
    available_funds: 1_100,
    day_change: -220,
    day_change_pct: -0.4,
  },
];

type Item = { id: string; symbol: string; account_id: string };
const items: Item[] = [
  { id: '1', symbol: 'AAPL', account_id: 'A1' },
  { id: '2', symbol: 'MSFT', account_id: 'A1' },
  { id: '3', symbol: 'NVDA', account_id: 'A2' },
];

export const AccountSelector_Detailed = () => {
  const { colorMode, toggleColorMode } = useColorMode();
  const [selected, setSelected] = React.useState('all');

  return (
    <Box p={6}>
      <Text
        as="button"
        onClick={toggleColorMode}
        style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.12)' }}
      >
        Toggle mode ({colorMode})
      </Text>
      <Box mt={4}>
        <AccountSelector accounts={accounts} selectedAccount={selected} onAccountChange={setSelected} />
      </Box>
    </Box>
  );
};

export const AccountFilterWrapper_Example = () => {
  return (
    <Box p={6}>
      <AccountFilterWrapper
        data={items}
        accounts={accounts}
        config={{ showSummary: true, showAllOption: true, variant: 'detailed' }}
      >
        {(filtered) => (
          <Box mt={3} borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card" p={4}>
            <Text fontWeight="semibold" color="fg.default">
              Filtered symbols
            </Text>
            <Text fontSize="sm" color="fg.muted">
              {filtered.map((x) => x.symbol).join(', ') || '—'}
            </Text>
          </Box>
        )}
      </AccountFilterWrapper>
    </Box>
  );
};


