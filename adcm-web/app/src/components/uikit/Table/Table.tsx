import React, { useMemo, forwardRef } from 'react';
import cn from 'classnames';

import TableHead from './TableHead/TableHead';
import Spinner from '@uikit/Spinner/Spinner';
import EmptyRow from './TableRow/EmptyRow';
import type { SortingProps } from '@uikit/types/list.types';
import type { TableColumn, TableSelectedAllOptions } from '@uikit/Table/Table.types';

import s from './Table.module.scss';
import { TableContext } from '@uikit/Table/TableContext';

type TableVariants = 'primary' | 'secondary' | 'tertiary' | 'quaternary';

export interface TableProps
  extends React.HTMLAttributes<HTMLDivElement>,
    Partial<SortingProps>,
    TableSelectedAllOptions {
  columns?: TableColumn[];
  children: React.ReactNode;
  variant?: TableVariants;
  isLoading?: boolean;
  spinner?: React.ReactNode;
  noData?: React.ReactNode;
  width?: string;
  dataTest?: string;
}

const defaultEmptyRowLength = 100;

const Table = forwardRef<HTMLTableElement, TableProps>(
  (
    {
      className,
      children,
      columns,
      sortParams,
      onSorting,
      isAllSelected,
      toggleSelectedAll,
      isLoading = false,
      variant = 'primary',
      spinner = <TableSpinner />,
      noData = <TableNoData />,
      width,
      dataTest = 'table',
      ...props
    },
    ref,
  ) => {
    const tableClasses = cn(s.table, s[`table_${variant}`]);
    const contextData = useMemo(
      () => ({ isAllSelected, toggleSelectedAll, sortParams, onSorting, columns }),
      [isAllSelected, toggleSelectedAll, sortParams, onSorting, columns],
    );

    return (
      <div className={cn(className, s.tableWrapper, 'scroll')} {...props} data-test={dataTest}>
        <TableContext.Provider value={contextData}>
          <table ref={ref} className={tableClasses} style={{ width: width }}>
            {columns?.length && <TableHead columns={columns} />}
            <TableBody>
              {isLoading && (
                <EmptyRow data-test="loading" columnCount={columns?.length || defaultEmptyRowLength}>
                  {spinner}
                </EmptyRow>
              )}
              {!isLoading && children}
              {!isLoading && (
                <EmptyRow
                  columnCount={columns?.length || defaultEmptyRowLength}
                  className={s.table__row_noData}
                  data-test="no-data"
                >
                  {noData}
                </EmptyRow>
              )}
            </TableBody>
          </table>
        </TableContext.Provider>
      </div>
    );
  },
);

export default Table;

const TableBody: React.FC<React.HTMLProps<HTMLTableSectionElement>> = ({ children }) => {
  return <tbody>{children}</tbody>;
};

const TableNoData = () => <span className={s.table__textNoData}>No data</span>;

const TableSpinner = () => (
  <div className={s.table__spinnerWrapper}>
    <Spinner />
  </div>
);
