import React from 'react';
import cn from 'classnames';
import s from './TableCell.module.scss';
import { AlignType } from '../Table.types';

export interface TableCellProps extends Omit<React.HTMLProps<HTMLTableCellElement>, 'align'> {
  align?: AlignType;
  tag?: 'th' | 'td';
  width?: string;
  minWidth?: string;
  isMultilineText?: boolean;
  hasIconOnly?: boolean;
}
const TableCell: React.FC<TableCellProps> = ({
  tag = 'td',
  align,
  width,
  minWidth,
  className,
  children,
  style,
  isMultilineText = false,
  hasIconOnly = false,
  ...props
}) => {
  const Tag = tag;
  const cellClasses = cn(className, s.tableCell, {
    [s.tableCell_oneLine]: !isMultilineText,
    [s.tableCell_iconOnly]: hasIconOnly,
    [s[`tableCell_align-${align}`]]: align,
  });

  return (
    <Tag className={cellClasses} {...props} style={{ ...style, width, minWidth }}>
      <div className={s.tableCell__inner}>{children}</div>
    </Tag>
  );
};
export default TableCell;
