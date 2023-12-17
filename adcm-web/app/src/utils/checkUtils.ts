type GetCallback<T, R> = (data: T) => R;

export const orElseGet = <T, R = T>(
  data: T | undefined | null,
  callback?: GetCallback<T, R> | null,
  placeholder: R = '-' as R,
): R => {
  if (Number.isNaN(data) || typeof data === 'undefined' || data === null) return placeholder as R;

  return (callback ? callback(data) : data) as R;
};
