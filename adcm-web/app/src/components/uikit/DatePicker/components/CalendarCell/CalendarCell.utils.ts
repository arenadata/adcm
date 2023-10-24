import { isEqual } from '@utils/date';
import { getToday, getMonth, startOfDay, isDateInRange } from '@utils/date/calendarUtils';
import s from './CalendarCell.module.scss';
import cn from 'classnames';

interface GetDayClassesProps {
  day: Date;
  selectedMonth: Date;
  selectedDate?: Date;
  startDate?: Date;
  endDate?: Date;
}

export const getDayClasses = ({ day, selectedMonth, selectedDate, startDate, endDate }: GetDayClassesProps) => {
  const today = getToday();
  const curActiveDate = selectedDate ? selectedDate : today;

  const isDayInThisMonth = getMonth(day) === getMonth(selectedMonth);
  const isDaySelected = isEqual(startOfDay(day), startOfDay(curActiveDate));
  const isToday = isEqual(startOfDay(day), startOfDay(today));

  const isUnavailable = !isDateInRange(day, startDate, endDate) && isDayInThisMonth && !isToday && !isDaySelected;
  const isDisabled = !isDayInThisMonth && !isToday && !isDaySelected;

  return cn(s.calendarCell, {
    [s.calendarCell__unavailable]: isUnavailable,
    [s.calendarCell__disabled]: isDisabled,
    [s.calendarCell__selectedDate]: isDaySelected && isDayInThisMonth,
    [s.calendarCell__today]: isToday && !isDaySelected,
    [s.calendarCell__thisMonth]: isDayInThisMonth && !isToday && !isUnavailable && !isDaySelected,
  });
};
