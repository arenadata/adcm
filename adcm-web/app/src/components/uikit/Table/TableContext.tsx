import React, { useContext } from 'react';
import { TableSelectedAllOptions } from './Table.types';
import { SortingProps } from '@uikit/types/list.types';

type TableContextOptions = TableSelectedAllOptions & Partial<SortingProps>;

export const TableContext = React.createContext<TableContextOptions>({} as TableContextOptions);

// eslint-disable-next-line react-refresh/only-export-components
export const useTableContext = (): TableContextOptions => {
  const ctx = useContext<TableContextOptions>(TableContext);
  if (!ctx) {
    throw new Error('useContext must be inside a Provider with a value');
  }
  return ctx;
};
