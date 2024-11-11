import type { ChangeEvent } from 'react';
import React from 'react';
import type { TableCellProps } from '@uikit/Table/TableCell/TableCell';
import TableCell from '@uikit/Table/TableCell/TableCell';
import Checkbox from '@uikit/Checkbox/Checkbox';
import s from './TableCell.module.scss';
import Icon from '@uikit/Icon/Icon';
import { useTableContext } from '@uikit/Table/TableContext';

const TableHeadCellCheckbox: React.FC<Omit<TableCellProps, 'children'>> = (props) => {
  const { isAllSelected, toggleSelectedAll } = useTableContext();
  const handleAllChange = (e: ChangeEvent<HTMLInputElement>) => {
    toggleSelectedAll?.(e.target.checked);
  };
  return (
    <TableCell {...props} width="60px" tag="th">
      <Checkbox checked={isAllSelected} onChange={handleAllChange} />
      <Icon name="chevron" className={s.tableHeadCellCheckbox__chevron} size={10} />
    </TableCell>
  );
};
export default TableHeadCellCheckbox;
