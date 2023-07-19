import { ChangeEvent, Dispatch, SetStateAction, useCallback, useMemo } from 'react';

export const useSelectedRows = <Entity, Key = string>(
  entitiesList: Entity[],
  getKey: (entity: Entity) => Key,
  selectedKeys: Key[],
  setSelectedKeys: Dispatch<SetStateAction<Key[]>>,
) => {
  const isAllItemsSelected = useMemo(() => {
    if (entitiesList.length === 0) return false;

    return entitiesList.every((item) => selectedKeys.includes(getKey(item)));
  }, [entitiesList, selectedKeys, getKey]);

  const toggleSelectedAllItems = useCallback(
    (isAllSelected: boolean) => {
      const list = isAllSelected ? entitiesList.map((entity) => getKey(entity)) : [];

      setSelectedKeys(list);
    },
    [entitiesList, getKey, setSelectedKeys],
  );

  const toggleOneItem = useCallback(
    (entity: Entity, isSelected: boolean) => {
      setSelectedKeys((prev) => {
        const newSelectedRows = [...prev];

        const key = getKey(entity);

        const index = newSelectedRows.indexOf(key);
        const isCurrentSelected = index > -1;

        if (isSelected && !isCurrentSelected) {
          // add entity key to selected rows
          newSelectedRows.splice(index, 0, key);
        } else if (!isSelected && isCurrentSelected) {
          // remove entity key from selected rows
          newSelectedRows.splice(index, 1);
        }

        return newSelectedRows;
      });
    },
    [getKey, setSelectedKeys],
  );

  const getHandleSelectedItem = useCallback(
    (entity: Entity) => (e: ChangeEvent<HTMLInputElement>) => {
      toggleOneItem(entity, e.target.checked);
    },
    [toggleOneItem],
  );

  const isItemSelected = useCallback(
    (entity: Entity) => selectedKeys.indexOf(getKey(entity)) > -1,
    [selectedKeys, getKey],
  );

  return {
    isAllItemsSelected,
    toggleSelectedAllItems,
    toggleOneItem,
    getHandleSelectedItem,
    isItemSelected,
  };
};
