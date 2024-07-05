import { useState, useCallback } from 'react';

export const useExpandableTable = <T>() => {
  const [expandableRows, setExpandableRows] = useState<Set<T>>(new Set());

  const toggleRow = useCallback(
    (key: T) => {
      setExpandableRows((prev) => {
        const prepState = new Set<T>([...prev]);

        if (prepState.has(key)) {
          prepState.delete(key);
        } else {
          prepState.add(key);
        }
        return prepState;
      });
    },
    [setExpandableRows],
  );

  const changeExpandedRowsState = useCallback(
    (rows: { key: T; isExpand: boolean }[]) => {
      setExpandableRows((prev) => {
        const prepState = new Set<T>([...prev]);

        rows.forEach((row) => {
          if (prepState.has(row.key) && !row.isExpand) {
            prepState.delete(row.key);
          } else if (row.isExpand) {
            prepState.add(row.key);
          }
        });

        return prepState;
      });
    },
    [setExpandableRows],
  );

  return {
    expandableRows,
    toggleRow,
    changeExpandedRowsState,
    setExpandableRows,
  };
};
