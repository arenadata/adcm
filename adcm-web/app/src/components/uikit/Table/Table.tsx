import React, { useMemo } from 'react';
import cn from 'classnames';

import TableHead from './TableHead/TableHead';
import Spinner from '@uikit/Spinner/Spinner';
import EmptyRow from './TableRow/EmptyRow';
import { SortingProps } from '@uikit/types/list.types';
import { TableColumn, TableSelectedAllOptions } from '@uikit/Table/Table.types';

import s from './Table.module.scss';
import { TableContext } from '@uikit/Table/TableContext';

type TableVariants = 'primary' | 'secondary' | 'tertiary' | 'quaternary';

export interface TableProps
  extends React.HTMLAttributes<HTMLDivElement>,
    Partial<SortingProps>,
    TableSelectedAllOptions {
  columns: TableColumn[];
  children: React.ReactNode;
  variant?: TableVariants;
  isLoading?: boolean;
  spinner?: React.ReactNode;
  noData?: React.ReactNode;
  width?: string;
}

const Table: React.FC<TableProps> = ({
  className,
  children,
  columns,
  sortParams,
  onSorting,
  isAllSelected,
  toggleSelectedAll,
  isLoading = false,
  variant = 'primary',
  spinner = <Spinner />,
  noData = <TableNoData />,
  width,
  ...props
}) => {
  const tableClasses = cn(s.table, s[`table_${variant}`]);
  const contextData = useMemo(
    () => ({ isAllSelected, toggleSelectedAll, sortParams, onSorting }),
    [isAllSelected, toggleSelectedAll, sortParams, onSorting],
  );
  return (
    <div className={cn(className, s.tableWrapper, 'scroll')} {...props}>
      <TableContext.Provider value={contextData}>
        <table className={tableClasses} style={{ width: width }}>
          <TableHead columns={columns} />
          <TableBody>
            {isLoading && <EmptyRow columnCount={columns.length}>{spinner}</EmptyRow>}
            {!isLoading && children}
            {!isLoading && (
              <EmptyRow columnCount={columns.length} className={s.table__row_noData}>
                {noData}
              </EmptyRow>
            )}
          </TableBody>
        </table>
      </TableContext.Provider>
    </div>
  );
};
export default Table;

const TableBody: React.FC<React.HTMLProps<HTMLTableSectionElement>> = ({ children }) => {
  return <tbody>{children}</tbody>;
};

const TableNoData = () => <span>No Data</span>;
