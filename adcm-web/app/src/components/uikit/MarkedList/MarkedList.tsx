import React from 'react';
import s from './MarkedList.module.scss';

interface MarkedListProps<T> {
  list: T[];
  renderItem: (item: T) => React.ReactNode;
  getItemKey: (item: T) => string | number;
}

const MarkedList = <T,>({ list, getItemKey, renderItem }: MarkedListProps<T>) => {
  if (list.length === 0) return null;

  return (
    <ul className={s.markedList}>
      {list.map((item) => {
        return (
          <li className={s.markedList__item} key={getItemKey(item)}>
            {renderItem(item)}
          </li>
        );
      })}
    </ul>
  );
};

export default MarkedList;
