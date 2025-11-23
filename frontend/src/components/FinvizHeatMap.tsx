import React from 'react';
import {
  Box,
  Text,
  HStack,
  VStack,
  Badge,
  Tooltip,
  useColorModeValue,
} from '@chakra-ui/react';
import {
  ResponsiveContainer,
  Treemap,
  Cell,
  Tooltip as RechartsTooltip,
} from 'recharts';

interface FinvizData {
  name: string;
  size: number;
  change: number;
  sector: string;
  value: number;
}

interface FinvizHeatMapProps {
  data: FinvizData[];
  height?: number;
  showLegend?: boolean;
  title?: string;
}

const HEAT_MAP_COLORS = {
  strong_positive: '#00C851',   // Bright green
  positive: '#39CCCC',          // Light teal  
  neutral: '#FFBB33',           // Amber
  negative: '#FF8800',          // Orange
  strong_negative: '#FF4444',   // Red
};

const getHeatMapColor = (changePercent: number): string => {
  if (changePercent > 3) return HEAT_MAP_COLORS.strong_positive;
  if (changePercent > 1) return HEAT_MAP_COLORS.positive;
  if (changePercent > -1) return HEAT_MAP_COLORS.neutral;
  if (changePercent > -3) return HEAT_MAP_COLORS.negative;
  return HEAT_MAP_COLORS.strong_negative;
};

const CustomTooltip = ({ active, payload }: any) => {
  const bgColor = useColorModeValue('white', 'gray.800');

  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <Box
        bg={bgColor}
        p={3}
        border="1px solid"
        borderColor="gray.200"
        borderRadius="md"
        boxShadow="lg"
        fontSize="sm"
      >
        <Text fontWeight="bold">{data.name}</Text>
        <Text>Value: ${data.value.toLocaleString()}</Text>
        <Text color={data.change >= 0 ? 'green.500' : 'red.500'}>
          Change: {data.change >= 0 ? '+' : ''}{data.change.toFixed(2)}%
        </Text>
        <Text fontSize="xs" color="gray.500">{data.sector}</Text>
      </Box>
    );
  }
  return null;
};

const renderCustomizedLabel = (entry: any) => {
  if (entry.depth === 1) {
    const fontSize = Math.max(8, Math.min(16, entry.width / 8));
    const textColor = '#000';

    // Only show label if cell is large enough
    if (entry.width > 40 && entry.height > 25) {
      return (
        <g>
          <text
            x={entry.x + entry.width / 2}
            y={entry.y + entry.height / 2 - 5}
            textAnchor="middle"
            fill={textColor}
            fontSize={fontSize}
            fontWeight="bold"
          >
            {entry.name}
          </text>
          <text
            x={entry.x + entry.width / 2}
            y={entry.y + entry.height / 2 + fontSize - 2}
            textAnchor="middle"
            fill={textColor}
            fontSize={Math.max(6, fontSize - 2)}
          >
            {entry.change > 0 ? '+' : ''}{entry.change.toFixed(1)}%
          </text>
        </g>
      );
    }
  }
  return null;
};

const CustomContent: React.FC<any> = (props) => {
  return renderCustomizedLabel(props) as any;
};

const FinvizHeatMap: React.FC<FinvizHeatMapProps> = ({
  data,
  height = 300,
  showLegend = true,
  title = "Portfolio Heat Map"
}) => {
  // Prepare data with colors
  const heatMapData = data.map(item => ({
    ...item,
    color: getHeatMapColor(item.change)
  }));

  return (
    <VStack spacing={3} align="stretch">
      {title && (
        <Text fontSize="md" fontWeight="semibold">{title}</Text>
      )}

      <Box border="1px solid" borderColor="gray.200" borderRadius="md" overflow="hidden">
        <ResponsiveContainer width="100%" height={height}>
          <Treemap
            data={heatMapData}
            dataKey="size"
            stroke="#fff"
            strokeWidth={1}
            content={<CustomContent />}
          >
            {heatMapData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
            <RechartsTooltip content={<CustomTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      </Box>

      {showLegend && (
        <HStack spacing={4} justify="center" wrap="wrap" fontSize="xs">
          <HStack>
            <Box w={3} h={3} bg={HEAT_MAP_COLORS.strong_positive} />
            <Text>&gt;3%</Text>
          </HStack>
          <HStack>
            <Box w={3} h={3} bg={HEAT_MAP_COLORS.positive} />
            <Text>1-3%</Text>
          </HStack>
          <HStack>
            <Box w={3} h={3} bg={HEAT_MAP_COLORS.neutral} />
            <Text>-1% to 1%</Text>
          </HStack>
          <HStack>
            <Box w={3} h={3} bg={HEAT_MAP_COLORS.negative} />
            <Text>-1% to -3%</Text>
          </HStack>
          <HStack>
            <Box w={3} h={3} bg={HEAT_MAP_COLORS.strong_negative} />
            <Text>&lt;-3%</Text>
          </HStack>
        </HStack>
      )}
    </VStack>
  );
};

export default FinvizHeatMap; 