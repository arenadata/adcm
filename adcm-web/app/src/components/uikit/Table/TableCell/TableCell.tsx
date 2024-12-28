import type React from 'react';
import { useState, useCallback } from 'react';
import cn from 'classnames';
import s from './TableCell.module.scss';
import type { AlignType } from '../Table.types';
import { useTableContext } from '@uikit/Table/TableContext';

export interface TableCellProps extends Omit<React.HTMLProps<HTMLTableCellElement>, 'align'> {
  align?: AlignType;
  tag?: 'th' | 'td';
  width?: string;
  minWidth?: string;
  isMultilineText?: boolean;
  hasIconOnly?: boolean;
}

const getElementIndex = (el: HTMLElement) => Array.from(el.parentNode?.children || []).indexOf(el);

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
  const [dataTest, setDataTest] = useState('');
  const Tag = tag;
  const cellClasses = cn(className, s.tableCell, {
    [s.tableCell_oneLine]: !isMultilineText,
    [s.tableCell_iconOnly]: hasIconOnly,
    [s[`tableCell_align-${align}`]]: align,
  });
  const { columns } = useTableContext();

  const refCallback = useCallback(
    (cell: HTMLTableCellElement) => {
      if (!cell || !columns) return;
      const index = getElementIndex(cell);

      if (index === -1) return;

      setDataTest(columns[index].name.toLowerCase());
    },
    [columns],
  );

  return (
    <Tag
      ref={refCallback}
      className={cellClasses}
      {...props}
      data-test={dataTest}
      style={{ ...style, width, minWidth }}
    >
      <div className={s.tableCell__inner}>{children}</div>
    </Tag>
  );
};
export default TableCell;
