import { format } from '@utils/date';
import {
  addDays,
  eachDayOfInterval,
  endOfMonth,
  getDay,
  getWeekOfMonth,
  isMonday,
  startOfDay,
  startOfMonth,
} from '@utils/date/calendarUtils';
import type { CalendarMap } from '@uikit/DatePicker/DatePicker.types';

const getActiveMonthInterval = (dateFromProps: Date) =>
  eachDayOfInterval({ start: startOfMonth(dateFromProps), end: endOfMonth(dateFromProps) });

const fillCalendarMapWithPrevMonthDays = (calendarMap: Date[][], currentFirstDate: Date) => {
  const lastEmptyDay = calendarMap[0].findIndex((item) => !!item);
  for (let i = 0; i < lastEmptyDay; i += 1) {
    calendarMap[0][i] = addDays(currentFirstDate, -(lastEmptyDay - i));
  }
};

const fillCalendarMapWithNextMonthDays = (calendarMap: Date[][], currentLastDate: Date) => {
  const lastCurrentMonthWeek = calendarMap.findIndex((item) => item.length < 7);
  const firstDayOfNextMonth = calendarMap[lastCurrentMonthWeek].length;
  for (let i = lastCurrentMonthWeek, j = firstDayOfNextMonth, k = 1; i < 6; i += 1, j = 0) {
    for (; j < 7; j += 1, k += 1) {
      calendarMap[i][j] = addDays(currentLastDate, k);
    }
  }
};

export const getCalendarMap = (date: Date) => {
  const currentFirstDate = startOfMonth(date);
  const currentLastDate = startOfDay(endOfMonth(date));
  const startsFromMonday = isMonday(currentFirstDate);

  const calendarMap = getActiveMonthInterval(date).reduce(
    (calendarMap: CalendarMap, next) => {
      const day = getDay(next) === 0 ? 6 : getDay(next) - 1;
      const week = getWeekOfMonth(next, { weekStartsOn: 1 }) - 1;
      calendarMap[week][day] = next;
      return calendarMap;
    },
    [[], [], [], [], [], []],
  );

  if (!startsFromMonday) {
    fillCalendarMapWithPrevMonthDays(calendarMap, currentFirstDate);
  }

  fillCalendarMapWithNextMonthDays(calendarMap, currentLastDate);

  return calendarMap;
};

export const formatDate = (date?: Date) => (date ? format(date, 'dd/MM/yyyy HH:mm') : '');
