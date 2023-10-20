import { useState, useCallback } from 'react';

type StorageProps<T> = {
  key: string;
  initData?: T;
};

type StorageReturnProps<T> = [storageData: T | null, setItem: (itemData: T) => void, removeItem: () => void];

export const useLocalStorage = <T>({ key, initData }: StorageProps<T>): StorageReturnProps<T> => {
  const [storageData, setStorageData] = useState<T | null>(() => {
    const storageData = localStorage.getItem(key) as string;
    try {
      const data = JSON.parse(storageData) as T;
      if (data) return data;
      if (initData) {
        localStorage.setItem(key, JSON.stringify(initData));
        return initData;
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
