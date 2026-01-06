import React from 'react';
import { Box, Text } from '@chakra-ui/react';
import { useColorMode } from '../theme/colorMode';
import FinvizHeatMap from '../components/charts/FinvizHeatMap';
import TradingViewChart from '../components/charts/TradingViewChart';
import SymbolChartWithMarkers from '../components/charts/SymbolChartWithMarkers';

export default {
  title: 'DesignSystem/Charts',
};

const heatmap = [
  { name: 'AAPL', size: 10, change: 1.8, sector: 'Tech', value: 182_000 },
  { name: 'MSFT', size: 9, change: -0.7, sector: 'Tech', value: 165_000 },
  { name: 'NVDA', size: 8, change: 3.6, sector: 'Tech', value: 144_000 },
  { name: 'AMZN', size: 7, change: -2.3, sector: 'Consumer', value: 128_000 },
  { name: 'TSLA', size: 6, change: 0.4, sector: 'Auto', value: 110_000 },
  { name: 'JPM', size: 5, change: -4.1, sector: 'Financials', value: 92_000 },
];

export const FinvizHeatMap_Basic = () => (
  <Box p={6}>
    <FinvizHeatMap data={heatmap as any} height={360} />
  </Box>
);

export const TradingViewChart_Example = () => {
  const { colorMode, toggleColorMode } = useColorMode();
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
        <TradingViewChart symbol="AAPL" height={520} />
      </Box>
      <Text mt={3} fontSize="xs" color="fg.muted">
        Note: this loads TradingView’s external embed script at runtime.
      </Text>
    </Box>
  );
};

export const SymbolChartWithMarkers_Example = () => {
  const now = Date.now();
  const day = 86400_000;
  const bars = Array.from({ length: 60 }).map((_, i) => {
    const t = new Date(now - (60 - i) * day).toISOString();
    const base = 100 + i * 0.4;
    return { time: t, open: base - 0.6, high: base + 1.2, low: base - 1.1, close: base + (i % 2 ? 0.7 : -0.3) };
  });
  const buys = [{ time: bars[10].time, price: 102.3, type: 'BUY' as const }];
  const sells = [{ time: bars[40].time, price: 114.1, type: 'SELL' as const }];
  const dividends = [{ time: bars[25].time, amount: 0.22 }];

  return (
    <Box p={6}>
      <Box borderWidth="1px" borderColor="border.subtle" borderRadius="xl" bg="bg.card" p={3}>
        <SymbolChartWithMarkers bars={bars as any} buys={buys as any} sells={sells as any} dividends={dividends as any} height={420} />
      </Box>
      <Text mt={3} fontSize="xs" color="fg.muted">
        Note: this loads LightweightCharts from a CDN at runtime.
      </Text>
    </Box>
  );
};


