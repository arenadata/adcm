type GetKeyCallback<T> = (item: T) => PropertyKey;

export function arrayToHash<T>(items: T[], getKey: GetKeyCallback<T>): Record<PropertyKey, T> {
  const hash = items.reduce((acc: Record<PropertyKey, T>, current: T) => {
    const key = getKey(current);
    acc[key] = current;
    return acc;
  }, {});

  return hash;
}

export const findBy = <T>(list: T[], field: keyof T, value: unknown) => {
  return list.find((item) => item[field] === value);
};
