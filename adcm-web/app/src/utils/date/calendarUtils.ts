import { localDateToUtc } from '@utils/date/utcUtils';

import {
  compareAsc,
  addMonths,
  getMonth,
  getYear,
  startOfDay,
  endOfDay,
  getDate,
  addDays,
  eachDayOfInterval,
  endOfMonth,
  getDay,
  getWeekOfMonth,
  isMonday,
  startOfMonth,
} from 'date-fns';
import { isEqual } from '@utils/date/index';

const getToday = () => {
  const localToday = new Date();

  // TODO: it's very ugly, but it's fast. Must rework in the future
  return localDateToUtc(localToday);
};

const getStartDayEndDay = (startDateTime = new Date(), endDateTime = new Date()): [number, number] => {
  return [startOfDay(localDateToUtc(startDateTime)).getTime(), endOfDay(localDateToUtc(endDateTime)).getTime()];
};

const isDateLessThan = (date: Date, minDate?: Date) => !!minDate && compareAsc(minDate, date) === 1;

const isDateBiggerThan = (date: Date, maxDate?: Date) => !!maxDate && compareAsc(date, maxDate) === 1;

const isDateInRange = (date: Date, minDate?: Date, maxDate?: Date) => {
  const isBiggerThenStart = minDate ? isDateBiggerThan(date, minDate) || isEqual(date, minDate) : true;
  const isLesThenEnd = maxDate ? isDateLessThan(date, maxDate) || isEqual(date, maxDate) : true;

  return isBiggerThenStart && isLesThenEnd;
};

export {
  compareAsc,
  addMonths,
  getMonth,
  getYear,
  startOfDay,
  endOfDay,
  getDate,
  addDays,
  eachDayOfInterval,
  endOfMonth,
  getDay,
  getWeekOfMonth,
  isMonday,
  startOfMonth,
  getToday,
  getStartDayEndDay,
  isDateLessThan,
  isDateBiggerThan,
  isDateInRange,
};
