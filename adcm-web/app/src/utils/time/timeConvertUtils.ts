import { utcDateToLocal } from '@utils/date/utcUtils';

export const secondsToTime = (seconds: number): string => {
  const date = new Date();
  date.setHours(0);
  date.setMinutes(0);
  date.setSeconds(seconds);
  return utcDateToLocal(date).toISOString().slice(11, 19);
};
