import React, { useEffect, useRef } from 'react';
import {
  Box,
  CardBody,
  CardHeader,
  CardRoot,
  Text,
  Button,
  HStack,
  Badge,
  IconButton,
  Tooltip,
} from '@chakra-ui/react';
import { FiExternalLink, FiX } from 'react-icons/fi';

interface TradingViewChartProps {
  symbol: string;
  onClose?: () => void;
  height?: number;
  showHeader?: boolean;
  showControls?: boolean;
  interval?: string;
  theme?: 'light' | 'dark';
  style?: string;
  hideSymbolSearch?: boolean;
  autosize?: boolean;
}

const TradingViewChart: React.FC<TradingViewChartProps> = ({
  symbol,
  onClose,
  height = 500,
  showHeader = true,
  showControls = true,
  interval = "D",
  theme = "light",
  style = "1",
  hideSymbolSearch = false,
  autosize = true,
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;

    // Clear previous chart
    chartRef.current.innerHTML = '';

    // Create TradingView script
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
    script.async = true;

    // Enhanced TradingView configuration with auth
    const config = {
      autosize: autosize,
      width: autosize ? undefined : "100%",
      height: autosize ? undefined : height - (showHeader ? 60 : 0),
      symbol: `NASDAQ:${symbol}`,
      interval: interval,
      timezone: "America/New_York",
      theme: theme,
      style: style,
      locale: "en",
      enable_publishing: false,
      allow_symbol_change: !hideSymbolSearch,
      calendar: false,
      support_host: "https://www.tradingview.com",
      // Authentication and enhanced features
      show_popup_button: true,
      popup_width: "1000",
      popup_height: "650",
      // Professional features (lean default - no indicators on load)
      details: false,
      hotlist: false,
      studies: [],
      // Enhanced toolbar
      toolbar_bg: "#f1f3f6",
      withdateranges: true,
      hide_side_toolbar: false,
      // Data source
      datafeed: "prod",
      // Login integration (using import.meta.env for Vite)
      customer: import.meta.env?.VITE_TRADINGVIEW_CUSTOMER || undefined,
      tradingview_customer: import.meta.env?.VITE_TRADINGVIEW_CUSTOMER || undefined,
    };

    script.innerHTML = JSON.stringify(config);
    chartRef.current.appendChild(script);

    return () => {
      if (chartRef.current) {
        chartRef.current.innerHTML = '';
      }
    };
  }, [symbol, height, showHeader, interval, theme, style, hideSymbolSearch, autosize]);

  const openInTradingView = () => {
    const url = `https://www.tradingview.com/chart/?symbol=NASDAQ:${symbol}`;
    window.open(url, '_blank', 'width=1200,height=800');
  };

  return (
    <CardRoot
      bg="bg.card"
      borderColor="border.subtle"
      borderWidth="1px"
      ref={containerRef}
      h={`${height}px`}
      position="relative"
      overflow="hidden"
      shadow="lg"
    >
      {showHeader && (
        <CardHeader py={3} px={4} borderBottom="1px solid" borderColor="border.subtle">
          <HStack justify="space-between" align="center">
            <HStack spacing={3}>
              <Text fontWeight="bold" fontSize="lg">{symbol}</Text>
              <Badge colorScheme="blue" variant="subtle">Live Chart</Badge>
            </HStack>

            {showControls && (
              <HStack spacing={2}>
                <Tooltip label="Open in TradingView">
                  <IconButton
                    aria-label="Open in TradingView"
                    size="sm"
                    variant="ghost"
                    onClick={openInTradingView}
                  >
                    <FiExternalLink />
                  </IconButton>
                </Tooltip>
                {onClose && (
                  <Tooltip label="Close chart">
                    <IconButton
                      aria-label="Close chart"
                      size="sm"
                      variant="ghost"
                      onClick={onClose}
                    >
                      <FiX />
                    </IconButton>
                  </Tooltip>
                )}
              </HStack>
            )}
          </HStack>
        </CardHeader>
      )}

      <CardBody p={0} h="full">
        <Box
          ref={chartRef}
          h="full"
          w="full"
          bg="bg.canvas"
        />
      </CardBody>
    </CardRoot>
  );
};

export default TradingViewChart; 