import type { PaginationParams } from '@models/table';
import { useMemo } from 'react';

interface UseLocalPaginationProps<T> {
  list: T[];
  paginationParams: PaginationParams;
}

export const useLocalPagination = <T>({ list, paginationParams }: UseLocalPaginationProps<T>) => {
  return useMemo(() => {
    const limit = paginationParams.perPage;
    const offset = paginationParams.perPage * paginationParams.pageNumber;
    return list.slice(offset, offset + limit);
  }, [list, paginationParams]);
};
