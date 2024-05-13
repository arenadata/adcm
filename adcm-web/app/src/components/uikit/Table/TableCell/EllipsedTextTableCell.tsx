import TableCell, { TableCellProps } from '@uikit/Table/TableCell/TableCell';
import s from './TableCell.module.scss';
import { orElseGet } from '@utils/checkUtils';

export interface EllipsedTextTableCellProps extends Omit<TableCellProps, 'isMultilineText'> {
  value: string;
  minWidth: string;
}

const EllipsedTextTableCell = ({ value, style, ...props }: EllipsedTextTableCellProps) => {
  const cellStyles = { ...style, maxWidth: 0 };

  return (
    <TableCell {...props} style={cellStyles}>
      <div className={s.tableCell__textWrap}>{orElseGet(value)}</div>
    </TableCell>
  );
};

export default EllipsedTextTableCell;
