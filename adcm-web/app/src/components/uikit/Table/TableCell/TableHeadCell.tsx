import React from 'react';
import { TableColumn } from '../Table.types';
import TableCell from './TableCell';
import SortingLabel from '@uikit/SortingLabel/SortingLabel';
import { useTableContext } from '../TableContext';

export type TableHeadCellProps = TableColumn & Omit<React.HTMLAttributes<HTMLTableCellElement>, 'align'>;
export const TableHeadCell: React.FC<TableHeadCellProps> = ({
  label,
  headerAlign,
  name,
  isSortable = false,
  ...props
}) => {
  const { sortParams, onSorting } = useTableContext();
  return (
    <TableCell align={headerAlign} tag="th" {...props}>
      {isSortable ? (
        <SortingLabel name={name} sortParams={sortParams} onSorting={onSorting}>
          {label}
        </SortingLabel>
      ) : (
        label
      )}
    </TableCell>
  );
};

export default TableHeadCell;
