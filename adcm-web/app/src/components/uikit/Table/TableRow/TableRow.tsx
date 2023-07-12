import React from 'react';

export type TableRowProps = React.HTMLAttributes<HTMLTableRowElement>;

const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(({ children, ...props }: TableRowProps, ref) => {
  return (
    <tr ref={ref} {...props}>
      {children}
    </tr>
  );
});

export default TableRow;
