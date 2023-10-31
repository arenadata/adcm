export const isPromiseFulfilled = <T>(p: PromiseSettledResult<T>): p is PromiseFulfilledResult<T> =>
  p.status === 'fulfilled';

export const isPromiseRejected = <T>(p: PromiseSettledResult<T>): p is PromiseRejectedResult => p.status === 'rejected';

export const fulfilledFilter = <T>(list: PromiseSettledResult<T>[]) =>
  list.filter(isPromiseFulfilled).map(({ value }) => value);

export const rejectedFilter = <T>(list: PromiseSettledResult<T>[]) =>
  list.filter(isPromiseRejected).map(({ reason }) => reason);

export const arePromisesResolved = <T>(promises: PromiseSettledResult<T>[]): boolean => {
  const responsesList = rejectedFilter(promises);
  if (responsesList.length > 0) {
    throw responsesList[0];
  }

  return true;
};
