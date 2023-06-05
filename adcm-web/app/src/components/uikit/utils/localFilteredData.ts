import { SortParams } from '@uikit/types/list.type';

export const getSortingData = <T>(data: T[], sortParams: SortParams) => {
  const sortField = sortParams.sortBy as keyof T;
  return [...data].sort((a, b) => {
    const aSortedField = a[sortField];
    const bSortedField = b[sortField];

    const sign = sortParams.sortDirection === 'asc' ? 1 : -1;

    if (aSortedField > bSortedField) return 1 * sign;
    if (bSortedField > aSortedField) return -1 * sign;

    return 0;
  });
};
