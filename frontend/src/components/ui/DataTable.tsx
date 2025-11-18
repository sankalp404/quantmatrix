import React from 'react';
import SortableTable, { Column } from '../SortableTable';

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  defaultSortBy?: string;
  defaultSortOrder?: 'asc' | 'desc';
  emptyMessage?: string;
}

function DataTable<T>({ data, columns, defaultSortBy, defaultSortOrder, emptyMessage }: DataTableProps<T>) {
  return (
    <SortableTable
      data={data}
      columns={columns}
      defaultSortBy={defaultSortBy}
      defaultSortOrder={defaultSortOrder}
      emptyMessage={emptyMessage}
    />
  );
}

export type { Column } from '../SortableTable';
export default DataTable;


