import type { HTMLAttributes } from 'react';
import type React from 'react';
import cn from 'classnames';

import s from './TableContainer.module.scss';

type variant = 'easy' | 'subPage';

interface TableContainerProps extends HTMLAttributes<HTMLDivElement> {
  variant?: variant;
  dataTest?: string;
}

const TableContainer: React.FC<TableContainerProps> = ({
  className,
  children,
  variant = 'easy',
  dataTest = 'table-container',
}) => {
  const classes = cn(className, s[`tableContainer_${variant}`]);
  return (
    <div className={classes} data-test={dataTest}>
      {children}
    </div>
  );
};

export default TableContainer;
