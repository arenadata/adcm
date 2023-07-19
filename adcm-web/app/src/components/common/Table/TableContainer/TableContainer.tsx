import React, { HTMLAttributes } from 'react';
import cn from 'classnames';

import s from './TableContainer.module.scss';

interface TableContainerProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'easy';
}

const TableContainer: React.FC<TableContainerProps> = ({ className, children, variant = 'easy' }) => {
  const classes = cn(className, s[`tableContainer_${variant}`]);
  return <div className={classes}>{children}</div>;
};

export default TableContainer;
