import type { EmptyTableFilter, PaginationParams, SortParams } from '@models/table';
import { queryParamSortBy } from '@constants';

const clearFilter = <F extends EmptyTableFilter>(filter: F) => {
  return Object.entries(filter).reduce(
    (res, [filterName, filterValue]) => {
      const isEmptyString = filterValue === '';
      const isEmptyArray = Array.isArray(filterValue) && filterValue.length === 0;

      if (!isEmptyString && !isEmptyArray) {
        res[filterName as keyof F] = filterValue;
      }
      return res;
    },
    {} as Record<keyof F, unknown>,
  );
};

export const prepareSorting = ({ sortBy: fieldName, sortDirection }: SortParams) => {
  const sign = sortDirection === 'desc' ? '-' : '';
  return {
    [queryParamSortBy]: `${sign}${fieldName}`,
  };
};

export const prepareLimitOffset = (paginationParams: PaginationParams) => {
  return {
    offset: paginationParams.pageNumber * paginationParams.perPage,
    limit: paginationParams.perPage,
  };
};

export const prepareQueryParams = <F extends EmptyTableFilter>(
  filter?: F,
  sortParams?: SortParams,
  paginationParams?: PaginationParams,
) => {
  const filterPart = filter ? clearFilter(filter) : {};
  const sortingPart = sortParams ? prepareSorting(sortParams) : {};
  const paginationPart = paginationParams ? prepareLimitOffset(paginationParams) : {};

  return {
    ...filterPart,
    ...sortingPart,
    ...paginationPart,
  };
};
