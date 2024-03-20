import { useState, useCallback } from 'react';

export const useExpandableTable = <T>() => {
  const [expandableRows, setExpandableRows] = useState<Set<T>>(new Set());

  const toggleRow = useCallback(
    (key: T) => {
      setExpandableRows((prev) => {
        if (prev.has(key)) {
          prev.delete(key);
        } else {
          prev.add(key);
        }
        return new Set([...prev]);
      });
    },
    [setExpandableRows],
  );

  return {
    expandableRows,
    toggleRow,
  };
};
