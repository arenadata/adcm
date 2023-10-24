import React from 'react';
import { orElseGet } from '@utils/checkUtils';
import { TableCell, TableCellProps } from '@uikit';
import { dateToString } from '@utils/date/dateConvertUtils';

interface DateTimeCellProps extends TableCellProps {
  value?: string;
}

const prepareDate = (value: string) => {
  if (!value.length) {
    return '';
  }
  return dateToString(new Date(value), { toUtc: true });
};

const DateTimeCell = ({ value }: DateTimeCellProps) => {
  const result = orElseGet(value, prepareDate);
  return (
    <TableCell isMultilineText width="210px" minWidth="125px">
      {result}
    </TableCell>
  );
};

export default DateTimeCell;
