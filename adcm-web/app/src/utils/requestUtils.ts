type ExecuteWithMinDelayArgs = {
  startDate: Date;
  delay: number;
  callback: () => void;
};

export const executeWithMinDelay = ({ startDate, delay, callback }: ExecuteWithMinDelayArgs) => {
  const curDate = new Date();
  const dateDiff = curDate.getTime() - startDate.getTime();
  setTimeout(() => {
    callback();
  }, Math.max(delay - dateDiff, 0));
};
