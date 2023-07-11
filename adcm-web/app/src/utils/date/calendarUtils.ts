import { localDateToUtc } from '@utils/date/utcUtils';

import {
  compareAsc,
  addMonths,
  getMonth,
  getYear,
  startOfDay,
  getDate,
  addDays,
  eachDayOfInterval,
  endOfMonth,
  getDay,
  getWeekOfMonth,
  isMonday,
  startOfMonth,
} from 'date-fns';

const getToday = () => {
  const localToday = new Date();

  // TODO: it's very ugly, but it's fast. Must rework in the future
  return localDateToUtc(localToday);
};

const isDateLessThan = (date: Date, minDate?: Date) => !!minDate && compareAsc(minDate, date) === 1;

const isDateBiggerThan = (date: Date, maxDate?: Date) => !!maxDate && compareAsc(date, maxDate) === 1;

export {
  compareAsc,
  addMonths,
  getMonth,
  getYear,
  startOfDay,
  getDate,
  addDays,
  eachDayOfInterval,
  endOfMonth,
  getDay,
  getWeekOfMonth,
  isMonday,
  startOfMonth,
  getToday,
  isDateLessThan,
  isDateBiggerThan,
};
