import React, { useState, useMemo, useCallback } from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  IconButton,
  HStack,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiChevronUp, FiChevronDown, FiMinus } from 'react-icons/fi';

// FIXED: Move getNestedValue outside component to avoid hoisting issues
const getNestedValue = (obj: any, path: string) => {
  return path.split('.').reduce((current, key) => current?.[key], obj);
};

interface SortConfig {
  key: string;
  direction: 'asc' | 'desc';
}

interface Column {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (value: any, row: any) => React.ReactNode;
  width?: string;
  align?: 'left' | 'center' | 'right';
}

interface SortableTableProps {
  data: any[];
  columns: Column[];
  onRowClick?: (row: any) => void;
  defaultSort?: { key: string; direction: 'asc' | 'desc' };
  size?: 'sm' | 'md' | 'lg';
  variant?: 'simple' | 'striped' | 'unstyled';
}

const SortableTable: React.FC<SortableTableProps> = ({
  data,
  columns,
  onRowClick,
  defaultSort,
  size = 'md',
  variant = 'simple'
}) => {
  const [sortConfig, setSortConfig] = useState<SortConfig | null>(
    defaultSort ? { key: defaultSort.key, direction: defaultSort.direction } : null
  );

  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');

  // Sort the data based on current sort configuration
  const sortedData = useMemo(() => {
    if (!sortConfig) return data;

    const sorted = [...data].sort((a, b) => {
      const aValue = getNestedValue(a, sortConfig.key);
      const bValue = getNestedValue(b, sortConfig.key);

      // Handle null/undefined values
      if (aValue == null && bValue == null) return 0;
      if (aValue == null) return 1;
      if (bValue == null) return -1;

      // Handle different data types
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        const comparison = aValue.toLowerCase().localeCompare(bValue.toLowerCase());
        return sortConfig.direction === 'asc' ? comparison : -comparison;
      }

      // Convert to string for comparison
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      const comparison = aStr.localeCompare(bStr);
      return sortConfig.direction === 'asc' ? comparison : -comparison;
    });

    return sorted;
  }, [data, sortConfig]);

  // Handle sort column click
  const handleSort = (key: string) => {
    const column = columns.find(col => col.key === key);
    if (!column?.sortable) return;

    let direction: 'asc' | 'desc' = 'asc';

    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }

    setSortConfig({ key, direction });
  };

  // Render sort icon
  const renderSortIcon = (column: Column) => {
    if (!column.sortable) return <FiMinus color="transparent" />;

    if (!sortConfig || sortConfig.key !== column.key) {
      return <FiMinus opacity={0.3} />;
    }

    return sortConfig.direction === 'asc' ? <FiChevronUp /> : <FiChevronDown />;
  };

  return (
    <TableContainer>
      <Table variant={variant} size={size}>
        <Thead>
          <Tr>
            {columns.map((column) => (
              <Th
                key={column.key}
                width={column.width}
                textAlign={column.align || 'left'}
                cursor={column.sortable ? 'pointer' : 'default'}
                onClick={() => handleSort(column.key)}
                borderColor={borderColor}
                _hover={column.sortable ? { bg: hoverBg } : undefined}
                userSelect="none"
              >
                <HStack spacing={1} justify={column.align === 'right' ? 'flex-end' : column.align === 'center' ? 'center' : 'flex-start'}>
                  <Text>{column.header}</Text>
                  {renderSortIcon(column)}
                </HStack>
              </Th>
            ))}
          </Tr>
        </Thead>
        <Tbody>
          {sortedData.map((row, index) => (
            <Tr
              key={row.id || index}
              cursor={onRowClick ? 'pointer' : 'default'}
              onClick={() => onRowClick?.(row)}
              _hover={onRowClick ? { bg: hoverBg } : undefined}
              borderColor={borderColor}
            >
              {columns.map((column) => {
                const value = getNestedValue(row, column.key);
                return (
                  <Td
                    key={column.key}
                    textAlign={column.align || 'left'}
                    borderColor={borderColor}
                  >
                    {column.render ? column.render(value, row) : value}
                  </Td>
                );
              })}
            </Tr>
          ))}
        </Tbody>
      </Table>
    </TableContainer>
  );
};

export default SortableTable; 