import { ChangeEvent, Dispatch, SetStateAction, useCallback, useMemo } from 'react';

export const useSelectedItems = <Entity, Key = string>(
  entitiesList: Entity[],
  getKey: (entity: Entity) => Key,
  selectedKeys: Key[],
  setSelectedKeys: Dispatch<SetStateAction<Key[]>>,
) => {
  const selectedCache = useMemo(() => new Set(selectedKeys), [selectedKeys]);

  const isAllItemsSelected = useMemo(() => {
    if (entitiesList.length === 0) return false;

    return entitiesList.every((item) => selectedCache.has(getKey(item)));
  }, [entitiesList, getKey, selectedCache]);

  const toggleSelectedAllItems = useCallback(
    (isAllSelected: boolean) => {
      const list = isAllSelected ? entitiesList.map((entity) => getKey(entity)) : [];

      setSelectedKeys(list);
    },
    [entitiesList, getKey, setSelectedKeys],
  );

  const toggleOneItem = useCallback(
    (entity: Entity, isSelected: boolean) => {
      const key = getKey(entity);
      const isCurrentSelected = selectedCache.has(key);
      if (isSelected && !isCurrentSelected) {
        selectedCache.add(key);
      } else {
        selectedCache.delete(key);
      }
      setSelectedKeys([...selectedCache]);
    },
    [getKey, setSelectedKeys, selectedCache],
  );

  const getHandlerSelectedItem = useCallback(
    (entity: Entity) => (e: ChangeEvent<HTMLInputElement>) => {
      toggleOneItem(entity, e.target.checked);
    },
    [toggleOneItem],
  );

  const isItemSelected = useCallback((entity: Entity) => selectedCache.has(getKey(entity)), [selectedCache, getKey]);

  return {
    isAllItemsSelected,
    toggleSelectedAllItems,
    toggleOneItem,
    getHandlerSelectedItem,
    isItemSelected,
  };
};
