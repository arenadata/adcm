export type SortDirection = 'asc' | 'desc';

export interface SortParams<T extends string = string> {
  sortBy: T;
  sortDirection: SortDirection;
}

export interface PaginationParams {
  pageNumber: number;
  perPage: number;
}

// eslint-disable-next-line @typescript-eslint/no-empty-object-type
export type EmptyTableFilter = {};

export type ListState<F extends EmptyTableFilter, E extends string = string> = {
  filter: F;
  sortParams: SortParams<E>;
  paginationParams: PaginationParams;
  requestFrequency: number;
};

export interface SortingProps<T extends string = string> {
  sortParams: SortParams<T>;
  onSorting: (sortParams: SortParams<T>) => void;
}
