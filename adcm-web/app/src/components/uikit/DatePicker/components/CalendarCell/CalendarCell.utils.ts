import { isEqual } from '@utils/date';
import { getToday, getMonth, startOfDay } from '@utils/date/calendarUtils';
import s from './CalendarCell.module.scss';
import cn from 'classnames';

interface GetDayClassesProps {
  day: Date;
  selectedMonth: Date;
  selectedDate?: Date;
}

export const getDayClasses = ({ day, selectedMonth, selectedDate }: GetDayClassesProps) => {
  const today = getToday();
  const curActiveDate = selectedDate ? selectedDate : today;

  return cn(s.calendarCell, s.calendarCell__date, {
    [s.calendarCell__thisMonth]: getMonth(day) === getMonth(selectedMonth),
    [s.calendarCell__selectedDate]: isEqual(startOfDay(day), startOfDay(curActiveDate)),
    [s.calendarCell__today]: isEqual(startOfDay(day), startOfDay(today)),
    [s.calendarCell__today_selected]:
      isEqual(startOfDay(day), startOfDay(today)) && isEqual(startOfDay(day), startOfDay(curActiveDate)),
  });
};
