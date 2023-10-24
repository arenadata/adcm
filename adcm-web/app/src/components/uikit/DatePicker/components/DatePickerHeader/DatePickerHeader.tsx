import IconButton from '@uikit/IconButton/IconButton';
import { ChangeMonthHandler } from '@uikit/DatePicker/DatePicker.types';
import { monthsDictionary } from '@uikit/DatePicker/DatePicker.constants';
import { getMonth, getYear } from '@utils/date/calendarUtils';
import s from './DatePickerHeader.module.scss';
import cn from 'classnames';

interface DatePickerHeaderProps {
  month: Date;
  onMonthChange: ChangeMonthHandler;
}

const DatePickerHeader = ({ month, onMonthChange }: DatePickerHeaderProps) => (
  <div className={s.datePickerHeader}>
    <IconButton
      icon="chevron"
      tabIndex={-1}
      onClick={onMonthChange('prev')}
      className={cn(s.monthButton, s.prevMonth)}
      size="small"
    />
    <div className={s.currentMonth}>{`${monthsDictionary[getMonth(month)]} ${getYear(month)}`}</div>
    <IconButton
      icon="chevron"
      tabIndex={-1}
      onClick={onMonthChange('next')}
      className={cn(s.monthButton, s.nextMonth)}
      size="small"
    />
  </div>
);

export default DatePickerHeader;
