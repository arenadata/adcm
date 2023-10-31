export type SortDirection = 'asc' | 'desc';

export interface SortParams {
  sortBy: string;
  sortDirection: SortDirection;
}

export interface PaginationParams {
  pageNumber: number;
  perPage: number;
}

export interface SortingProps {
  sortParams: SortParams;
  onSorting: (sortParams: SortParams) => void;
}
