import { useState } from 'react';

type StorageProps<T> = {
  key: string;
  initData?: T;
};

type StorageReturnProps<T> = [storageData: T | null, setItem: (itemData: T) => void, removeItem: () => void];

export const useLocalStorage = <T = string>({ key, initData }: StorageProps<T>): StorageReturnProps<T> => {
  const [storageData, setStorageData] = useState<T | null>(() => {
    const storageData1 = localStorage.getItem(key) as string;
    const data = JSON.parse(storageData1) as T;
    if (data) return data;
    if (initData) {
      localStorage.setItem(key, JSON.stringify(initData));
      return initData;
    }
    return null;
  });

  const setItem = (itemData: T) => {
    localStorage.setItem(key, JSON.stringify(itemData));
    setStorageData(itemData);
  };

  const removeItem = () => {
    localStorage.removeItem(key);
    setStorageData(null);
  };

  return [storageData, setItem, removeItem];
};
