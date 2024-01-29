import { useState, useEffect } from 'react';
import { useLocalStorage } from '@hooks/useLocalStorage';
import { PaginationParams } from '@models/table';
import { useStore } from '@hooks/useStore';

type UsePersistSettingsProps<T> = {
  localStorageKey: string;
  settings: T;
  isReadyToLoad: boolean;
  onSettingsLoaded: (settings: T) => void;
  loadedDataValidator?: (loadedData: T, data: T) => boolean;
};

const getTableSettingKey = (userName: string, tableKey: string) => `${userName}_${tableKey}`;

const defaultLoadedDataValidator = (loadedData: unknown, data: unknown) => {
  const dataType = typeof data;
  const loadedDataType = typeof loadedData;
  if (dataType !== loadedDataType) {
    return false;
  }

  // check 1st level keys similarity
  if (loadedData && loadedDataType === 'object' && data && dataType === 'object') {
    const loadedDataKeys = new Set(Object.keys(loadedData));
    const dataKeys = Object.keys(data);

    if (loadedDataKeys.size === dataKeys.length) {
      for (const key of dataKeys) {
        if (!loadedDataKeys.has(key)) {
          return false;
        }
      }

      return true;
    }
  }

  return false;
};

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
    if (props.isReadyToLoad && !isLoaded) {
      const loadedDataValidator = props.loadedDataValidator ?? defaultLoadedDataValidator;
      const isValid = loadedDataValidator(dataFromLocalStorage as T, props.settings);
      const validData = isValid ? dataFromLocalStorage : props.settings;

      if (validData) {
        props.onSettingsLoaded(validData);
        setIsLoaded(true);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.isReadyToLoad, props.loadedDataValidator, dataFromLocalStorage, isLoaded]);

  useEffect(() => {
    if (isLoaded) {
      storeDataToLocalStorage(props.settings);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, isLoaded]);
};

export { mergePaginationParams };
