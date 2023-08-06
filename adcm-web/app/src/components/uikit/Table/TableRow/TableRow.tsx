import React from 'react';
import s from './TableRow.module.scss';
import cn from 'classnames';

export type TableRowProps = React.HTMLAttributes<HTMLTableRowElement> & {
  isInactive?: boolean;
};

const TableRow = React.forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ children, className, isInactive = false, ...props }: TableRowProps, ref) => {
    const rowClasses = cn(className, { [s.tableRow_inactive]: isInactive });

    return (
      <tr ref={ref} className={rowClasses} {...props}>
        {children}
      </tr>
    );
  },
);

export default TableRow;
