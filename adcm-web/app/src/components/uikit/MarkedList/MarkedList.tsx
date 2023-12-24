import React from 'react';

interface MarkedListProps<T> {
  list: T[];
  renderItem: (item: T) => React.ReactNode;
  getItemKey: (item: T) => string | number;
}

const MarkedList = <T,>({ list, getItemKey, renderItem }: MarkedListProps<T>) => {
  if (list.length === 0) return null;

  return (
    <ul className={'marked-list'}>
      {list.map((item) => {
        return <li key={getItemKey(item)}>{renderItem(item)}</li>;
      })}
    </ul>
  );
};

export default MarkedList;
