export const getValueByPath = (object: unknown, path: string) => {
  return path.split('.').reduce((acc, c) => acc?.[c as keyof typeof object], object);
};

export const isObject = (obj: unknown) => Object.prototype.toString.call(obj) === '[object Object]';

type Scalar = number | string | boolean;
type Structure = object | object[] | Scalar;

type DefaultHandler<T> = (val: T) => T;

const defaultHandler = <T>(val: T): T => val;

export const structureTraversal = (
  structure: Structure,
  valueHandler: DefaultHandler<Structure> = defaultHandler,
  keyHandler: DefaultHandler<string> = (k) => k,
): Structure => {
  if (Array.isArray(structure)) {
    return structure.map((item) => structureTraversal(item, valueHandler, keyHandler));
  }
  if (isObject(structure)) {
    return Object.entries(structure).reduce(
      (res, [key, val]) => {
        res[keyHandler(key)] = structureTraversal(val, valueHandler, keyHandler);
        return res;
      },
      {} as Record<string, Structure>,
    );
  }

  return valueHandler ? valueHandler(structure) : structure;
};

export const objectTrim = (object: Structure) =>
  structureTraversal(object, (item) => (typeof item === 'string' ? item.trim() : item));

export const updateIfExists = <T>(
  items: T[],
  comparator: (item: T) => boolean,
  changes: (item: T) => Partial<T>,
): T[] => {
  let hasChanged = false;
  const newItems = items.map((item) => {
    if (comparator(item)) {
      hasChanged = true;
      return { ...item, ...changes(item) };
    }

    return item;
  });

  return hasChanged ? newItems : items;
};
