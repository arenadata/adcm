import { useState, useMemo } from 'react';
import DatePickerHeader from '../DatePickerHeader/DatePickerHeader';
import CalendarGrid from '../CalendarGrid/CalendarGrid';
import InputTime from '../InputTime/InputTime';
import DatePickerFooter from '../DatePickerFooter/DatePickerFooter';
import type { MonthSwitchDirections } from '@uikit/DatePicker/DatePicker.types';
import { getCalendarMap } from '@uikit/DatePicker/DatePicker.utils';
import { getToday, addMonths, isDateBiggerThan } from '@utils/date/calendarUtils';
import s from './CalendarPicker.module.scss';

export interface CalendarPickerProps {
  value?: Date;
  minDate?: Date;
  maxDate?: Date;
  hasError: boolean;
  onSet: (date?: Date) => void;
  onCancel: () => unknown;
}

const CalendarPicker = ({ value, minDate, maxDate, hasError, onSet, onCancel }: CalendarPickerProps) => {
  const currentDay = value ?? getToday();
  const initialActiveDate = maxDate && isDateBiggerThan(currentDay, maxDate) ? maxDate : currentDay;
  const [selectedDate, setSelectedDate] = useState(initialActiveDate);
  const [selectedMonth, setSelectedMonth] = useState(currentDay);

  const handleMonthChange = (direction: MonthSwitchDirections) => () => {
    setSelectedMonth(direction === 'prev' ? addMonths(selectedMonth, -1) : addMonths(selectedMonth, 1));
  };

  const handleSet = () => {
    onSet(selectedDate);
  };

  const calendarMap = useMemo(() => getCalendarMap(selectedMonth), [selectedMonth]);

  return (
    <div className={s.CalendarPicker}>
      <div className={s.CalendarPicker__section} data-test="data-picker-header">
        <DatePickerHeader onMonthChange={handleMonthChange} month={selectedMonth} />
      </div>
      <div className={s.CalendarPicker__section} data-test="data-picker-days">
        <CalendarGrid
          calendarMap={calendarMap}
          onDateClick={setSelectedDate}
          onMonthChange={handleMonthChange}
          minDate={minDate}
          maxDate={maxDate}
          selectedDate={selectedDate}
          selectedMonth={selectedMonth}
        />
      </div>
      <div className={s.CalendarPicker__section} data-test="data-picker-time">
        <InputTime date={selectedDate} onChange={setSelectedDate} />
      </div>
      <div className={s.CalendarPicker__section} data-test="data-picker-footer">
        <DatePickerFooter hasError={hasError} onSet={handleSet} onCancel={onCancel} />
      </div>
    </div>
  );
};

export default CalendarPicker;
