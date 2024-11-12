import { useState, useCallback } from 'react';
import { useStore } from '@hooks/useStore';

type StorageProps<T> = {
  key: string;
  initData?: T;
  isUserDependencies?: boolean;
};

type StorageReturnProps<T> = [storageData: T | null, setItem: (itemData: T) => void, removeItem: () => void];

export const useLocalStorage = <T>({
  key,
  initData,
  isUserDependencies = false,
}: StorageProps<T>): StorageReturnProps<T> => {
  const username = useStore(({ auth }) => auth.username);

  if (isUserDependencies) {
    key = `${username}/${key}`;
  }

  const [storageData, setStorageData] = useState<T | null>(() => {
    const storageData = localStorage.getItem(key) as string;
    try {
      const data = JSON.parse(storageData) as T;
      if (data) return data;
      if (initData) {
        const stringifyData = JSON.stringify(initData);
        localStorage.setItem(key, stringifyData);
        // have to parse stringified data again because getItem doesn't return undefined props from storage to return correct object
        return JSON.parse(stringifyData) as T;
      }
    } catch (e) {
      console.error(e);
    }

    return null;
  });

  const setItem = useCallback(
    (itemData: T) => {
      localStorage.setItem(key, JSON.stringify(itemData));
      setStorageData(itemData);
    },
    [key],
  );

  const removeItem = useCallback(() => {
    localStorage.removeItem(key);
    setStorageData(null);
  }, [key]);

  return [storageData, setItem, removeItem];
};
