import React from 'react';
import TableCell, { TableCellProps } from '@uikit/Table/TableCell/TableCell';
import s from './TableCell.module.scss';
import { orElseGet } from '@utils/checkUtils';

export interface BigTextCellProps extends TableCellProps {
  value: string;
}

const TableBigTextCell = ({ value }: BigTextCellProps) => {
  return (
    <TableCell>
      <div className={s.tableCell__textWrap}>{orElseGet(value)}</div>
    </TableCell>
  );
};

export default TableBigTextCell;
