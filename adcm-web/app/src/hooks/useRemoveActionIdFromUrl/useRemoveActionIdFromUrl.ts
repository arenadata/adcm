import { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { searchParamActionId } from '@constants';

export const useRemoveActionIdFromUrl = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  return useCallback(() => {
    if (searchParams.has(searchParamActionId)) {
      searchParams.delete(searchParamActionId);
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);
};
