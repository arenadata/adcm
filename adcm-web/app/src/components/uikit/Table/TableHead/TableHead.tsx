import React from 'react';
import { TableColumn } from '../Table.types';
import TableRow from '../TableRow/TableRow';
import { TableHeadCell, TableHeadCellCheckbox } from '../TableCell';

type TableHeadProps = {
  columns: TableColumn[];
};
const TableHead: React.FC<TableHeadProps> = ({ columns }) => {
  return (
    <thead>
      <TableRow>
        {columns.map(({ isCheckAll = false, ...column }) => (
          <React.Fragment key={column.name}>
            {isCheckAll && <TableHeadCellCheckbox />}
            {!isCheckAll && <TableHeadCell {...column} />}
          </React.Fragment>
        ))}
      </TableRow>
    </thead>
  );
};
export default TableHead;
