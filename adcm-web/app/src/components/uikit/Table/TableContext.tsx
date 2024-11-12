import React, { useContext } from 'react';
import type { TableColumn, TableSelectedAllOptions } from './Table.types';
import type { SortingProps } from '@uikit/types/list.types';

type TableContextOptions = TableSelectedAllOptions & Partial<SortingProps> & { columns?: TableColumn[] };

export const TableContext = React.createContext<TableContextOptions>({} as TableContextOptions);

export const useTableContext = (): TableContextOptions => {
  const ctx = useContext<TableContextOptions>(TableContext);
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
