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

type sortComparator<T> = (a: T, b: T) => number;
export const sortBy = <T>(list: T[], comparators: sortComparator<T>[]) => {
  return list.toSorted((a, b) => {
    for (const func of comparators) {
      const result = func(a, b);
      // if comparator return not 0 then we can resort a and b (return result). Else (comparator return 0) - a and b equal by this condition, and we try compare by next conditions
      if (result !== 0) {
        return result;
      }
    }

    // if all comparators returned 0 then a full equal b (return summary 0, too)
    return 0;
  });
};
