type GetCallback<T, R> = (data: T) => R;

export const orElseGet = <T, R = T>(
  data: T | undefined | null,
  callback?: GetCallback<T, R> | null,
  placeholder: R = '-' as R,
): R => {
  if (Number.isNaN(data) || typeof data === 'undefined' || data === null) return placeholder as R;

  return (callback ? callback(data) : data) as R;
};

export const isValueUnset = <T>(value: T | undefined | null): value is T =>
  typeof value === 'undefined' || value === null;

export const isValidData = <T>(data: T | undefined | null): data is T =>
  !(Number.isNaN(data) || typeof data === 'undefined' || data === null);
