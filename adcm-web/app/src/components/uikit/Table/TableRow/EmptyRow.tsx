import { forwardRef } from 'react';
import TableRow, { TableRowProps } from './TableRow';
import TableCell from '@uikit/Table/TableCell/TableCell';

export interface EmptyRowProps extends TableRowProps {
  columnCount?: number;
}

const EmptyRow = forwardRef<HTMLTableRowElement, EmptyRowProps>(({
  children,
  columnCount = 100,
  ...props
}, ref) => {
  return (
    <TableRow ref={ref} {...props}>
      <TableCell colSpan={columnCount} align="center">
        {children}
      </TableCell>
    </TableRow>
  );
});

export default EmptyRow;