export const deleteUndefinedItems = <T>(list: (T | undefined)[]) => {
  return list.filter((item): item is T => item !== undefined);
};
