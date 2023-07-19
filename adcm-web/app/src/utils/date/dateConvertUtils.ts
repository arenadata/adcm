import { format } from 'date-fns';
import { localDateToUtc } from './utcUtils';

type DateToStringOptions = {
  toUtc?: boolean;
  format?: string;
};

export const dateToString = (date: Date, options: DateToStringOptions = {}) => {
  const { format: formatStr = 'dd/MM/yyyy HH:mm:ss', toUtc = false } = options;
  const d1 = toUtc ? localDateToUtc(date) : date;
  return format(d1, formatStr);
};
