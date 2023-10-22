import { useState, useEffect } from 'react';
import { useLocalStorage } from '@hooks/useLocalStorage';
import { PaginationParams } from '@models/table';
import { useStore } from '@hooks/useStore';

type UsePersistSettingsProps<T> = {
  localStorageKey: string;
  settings: T;
  isReadyToLoad: boolean;
  onSettingsLoaded: (settings: T) => void;
};

const getTableSettingKey = (userName: string, tableKey: string) => `${userName}_${tableKey}`;

const mergePaginationParams = (perPage: number | undefined, paginationParams: PaginationParams): PaginationParams => {
  return perPage === undefined
    ? paginationParams
    : {
        ...paginationParams,
        perPage,
      };
};

export const usePersistSettings = <T>(props: UsePersistSettingsProps<T>, deps: unknown[]) => {
  const username = useStore(({ auth }) => auth.username);

  const [isLoaded, setIsLoaded] = useState(false);

  const [dataFromLocalStorage, storeDataToLocalStorage] = useLocalStorage({
    key: getTableSettingKey(username, props.localStorageKey),
    initData: props.settings,
  });

  useEffect(() => {
    if (props.isReadyToLoad && dataFromLocalStorage && !isLoaded) {
      props.onSettingsLoaded(dataFromLocalStorage);
      setIsLoaded(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.isReadyToLoad, dataFromLocalStorage, isLoaded]);

  useEffect(() => {
    if (isLoaded) {
      storeDataToLocalStorage(props.settings);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, isLoaded]);
};

export { mergePaginationParams };
