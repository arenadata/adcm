import React from 'react';
import cn from 'classnames';
import Icon from '../Icon/Icon';
import s from './SortingLabel.module.scss';
import { SortingProps, SortParams } from '@uikit/types/list.types';

interface SortingLabelProps extends Partial<SortingProps> {
  children: React.ReactNode;
  name: string;
  isSorted?: boolean;
}

const revertOrder = (order: SortParams['sortDirection']) => (order === 'asc' ? 'desc' : 'asc');
const SortingLabel: React.FC<SortingLabelProps> = ({ children, onSorting, name, sortParams }) => {
  const isSorted = name === sortParams?.sortBy;

  const wrapClasses = cn(s.sortingLabel, {
    'is-sorted': isSorted,
  });
  const arrowClasses = cn(
    s.sortingLabel__arrow,
    s[`sortingLabel__arrow_${(isSorted ? sortParams?.sortDirection : undefined) ?? 'asc'}`],
  );

  const handleClick = () => {
    const newSortDirection = isSorted ? revertOrder(sortParams.sortDirection) : 'asc';
    onSorting?.({ sortBy: name, sortDirection: newSortDirection });
  };
  return (
    <div className={wrapClasses} onClick={handleClick}>
      <div className={s.sortingLabel__label}>{children}</div>
      <Icon name="arrow-sorting" size={20} className={arrowClasses} />
    </div>
  );
};
export default SortingLabel;
