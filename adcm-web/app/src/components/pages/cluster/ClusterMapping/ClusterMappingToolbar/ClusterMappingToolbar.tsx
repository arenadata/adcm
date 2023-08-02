import React from 'react';
import { Button, SearchInput } from '@uikit';
import s from './ClusterMappingToolbar.module.scss';
import cn from 'classnames';

export interface ClusterMappingToolbarProps {
  className?: string;
  filter: string;
  filterPlaceHolder: string;
  isSaveDisabled: boolean;
  hasError: boolean;
  onFilterChange: (str: string) => void;
  onRevert: () => void;
  onSave: () => void;
}

const ClusterMappingToolbar = ({
  className = '',
  filter,
  filterPlaceHolder,
  isSaveDisabled,
  hasError,
  onFilterChange,
  onRevert,
  onSave,
}: ClusterMappingToolbarProps) => {
  // TODO: add debounce
  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange(event.target.value);
  };

  return (
    <div className={cn(s.clusterMappingToolbar, className)}>
      <SearchInput placeholder={filterPlaceHolder} value={filter} onChange={handleFilterChange} />
      <div className={s.clusterMappingToolbar__buttons}>
        <Button variant="secondary" onClick={onRevert}>
          Revert
        </Button>
        <Button onClick={onSave} disabled={isSaveDisabled} hasError={hasError}>
          Save mapping
        </Button>
      </div>
    </div>
  );
};

export default ClusterMappingToolbar;
