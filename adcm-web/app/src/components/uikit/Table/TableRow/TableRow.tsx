import React from 'react';
import TableCell from '@uikit/Table/TableCell/TableCell';

type TableRowProps = React.HTMLProps<HTMLTableRowElement>;
const TableRow: React.FC<TableRowProps> = ({ children, ...props }) => {
  return <tr {...props}>{children}</tr>;
};
export default TableRow;

export const EmptyRow: React.FC<TableRowProps & { columnCount?: number }> = ({
  children,
  columnCount = 100,
  ...props
}) => {
  return (
    <TableRow {...props}>
      <TableCell colSpan={columnCount} align="center">
        {children}
      </TableCell>
    </TableRow>
  );
};
