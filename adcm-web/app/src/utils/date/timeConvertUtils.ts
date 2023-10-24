import { intervalToDuration } from 'date-fns';

export const dateDuration = (dateTo: Date) => {
  const start = new Date();
  const { days = 0, hours = 0, minutes = 0, seconds = 0 } = intervalToDuration({ start, end: dateTo });

  const prepHours = hours.toString().padStart(2, '0');
  const prepMinutes = minutes.toString().padStart(2, '0');
  const prepSeconds = seconds.toString().padStart(2, '0');

  if (days === 0) return `${prepHours}:${prepMinutes}:${prepSeconds}`;

  const prepDays = `${days} ${days > 1 ? ' days ' : ' day '}`;
  return `${prepDays} ${prepHours}:${prepMinutes}:${prepSeconds}`;
};

export const secondsToDuration = (seconds: number) => {
  const curDate = new Date();
  const microSeconds = String(seconds).includes('.') ? `.${String(seconds).split('.')[1]}` : '';

  return `${dateDuration(new Date(curDate.getTime() + seconds * 1000))}${microSeconds}`;
};
