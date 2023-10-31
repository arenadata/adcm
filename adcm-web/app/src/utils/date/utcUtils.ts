export const localDateToUtc = (localDate: Date) => {
  const timestamp = localDate.getTime();
  const offset = localDate.getTimezoneOffset() * 60 * 1000; // minutes * 60sec * 1000ms

  return new Date(timestamp + offset);
};

export const utcDateToLocal = (utcDate: Date) => {
  const timestamp = utcDate.getTime();
  const offset = utcDate.getTimezoneOffset() * 60 * 1000; // minutes * 60sec * 1000ms

  return new Date(timestamp - offset);
};
