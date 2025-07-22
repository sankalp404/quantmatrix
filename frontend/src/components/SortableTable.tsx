import React, { useState, useMemo } from 'react';
import {
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  TableContainer,
  Box,
  Icon,
  HStack,
  Text,
  useColorModeValue,
} from '@chakra-ui/react';
import { FiChevronUp, FiChevronDown, FiMinus } from 'react-icons/fi';

export interface Column<T = any> {
  key: string;
  header: string;
  accessor: (item: T) => any;
  sortable?: boolean;
  sortType?: 'string' | 'number' | 'date';
  render?: (value: any, item: T) => React.ReactNode;
  width?: string;
  isNumeric?: boolean;
}

interface SortableTableProps<T = any> {
  data: T[];
  columns: Column<T>[];
  defaultSortBy?: string;
  defaultSortOrder?: 'asc' | 'desc';
  size?: 'sm' | 'md' | 'lg';
  variant?: 'simple' | 'striped' | 'unstyled';
  showHeader?: boolean;
  emptyMessage?: string;
  maxHeight?: string;
}

function SortableTable<T = any>({
  data,
  columns,
  defaultSortBy,
  defaultSortOrder = 'desc',
  size = 'md',
  variant = 'simple',
  showHeader = true,
  emptyMessage = 'No data available',
  maxHeight,
}: SortableTableProps<T>) {
  const [sortBy, setSortBy] = useState<string>(defaultSortBy || columns[0]?.key || '');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(defaultSortOrder);

  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');

  const handleSort = (columnKey: string) => {
    const column = columns.find(col => col.key === columnKey);
    if (!column?.sortable) return;

    if (sortBy === columnKey) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(columnKey);
      setSortOrder('desc');
    }
  };

  const getSortIcon = (columnKey: string) => {
    const column = columns.find(col => col.key === columnKey);
    if (!column?.sortable) return <Icon as={FiMinus} color="transparent" />;

    if (sortBy !== columnKey) {
      return <Icon as={FiMinus} color="gray.400" />;
    }

    return sortOrder === 'asc'
      ? <Icon as={FiChevronUp} color="blue.500" />
      : <Icon as={FiChevronDown} color="blue.500" />;
  };

  const sortedData = useMemo(() => {
    if (!sortBy || !data.length) return data;

    const column = columns.find(col => col.key === sortBy);
    if (!column) return data;

    return [...data].sort((a, b) => {
      const aValue = column.accessor(a);
      const bValue = column.accessor(b);

      // Handle null/undefined values
      if (aValue == null && bValue == null) return 0;
      if (aValue == null) return 1;
      if (bValue == null) return -1;

      let comparison = 0;

      switch (column.sortType) {
        case 'number':
          comparison = Number(aValue) - Number(bValue);
          break;
        case 'date':
          comparison = new Date(aValue).getTime() - new Date(bValue).getTime();
          break;
        case 'string':
        default:
          comparison = String(aValue).localeCompare(String(bValue));
          break;
      }

      return sortOrder === 'asc' ? comparison : -comparison;
    });
  }, [data, sortBy, sortOrder, columns]);

  if (!data.length) {
    return (
      <Box p={8} textAlign="center" color="gray.500">
        <Text>{emptyMessage}</Text>
      </Box>
    );
  }

  return (
    <TableContainer maxHeight={maxHeight} overflowY={maxHeight ? 'auto' : 'visible'}>
      <Table variant={variant} size={size}>
        {showHeader && (
          <Thead>
            <Tr>
              {columns.map((column) => (
                <Th
                  key={column.key}
                  onClick={() => handleSort(column.key)}
                  cursor={column.sortable ? 'pointer' : 'default'}
                  _hover={column.sortable ? { bg: hoverBg } : undefined}
                  userSelect="none"
                  isNumeric={column.isNumeric}
                  width={column.width}
                  borderColor={borderColor}
                >
                  <HStack spacing={2} justify={column.isNumeric ? 'flex-end' : 'flex-start'}>
                    <Text>{column.header}</Text>
                    {column.sortable && getSortIcon(column.key)}
                  </HStack>
                </Th>
              ))}
            </Tr>
          </Thead>
        )}
        <Tbody>
          {sortedData.map((item, index) => (
            <Tr key={index} _hover={{ bg: hoverBg }}>
              {columns.map((column) => {
                const value = column.accessor(item);
                const renderedValue = column.render ? column.render(value, item) : value;

                return (
                  <Td
                    key={column.key}
                    isNumeric={column.isNumeric}
                    borderColor={borderColor}
                  >
                    {renderedValue}
                  </Td>
                );
              })}
            </Tr>
          ))}
        </Tbody>
      </Table>
    </TableContainer>
  );
}

export default SortableTable; 