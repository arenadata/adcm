import type React from 'react';
import { Button, ButtonGroup, Panel, SearchInput, Switch, IconButton } from '@uikit';
import type { MappingFilter } from '../ClusterMapping.types';
import type { ActionState } from '@models/loadState';
import type { SortDirection } from '@models/table';
import s from './ClusterMappingToolbar.module.scss';
import cn from 'classnames';

export interface ClusterMappingToolbarProps {
  filter: MappingFilter;
  sortDirection: SortDirection;
  savingState: ActionState;
  hasSaveError: boolean;
  isValid: boolean;
  isMappingChanged: boolean;
  onFilterChange: (filter: Partial<MappingFilter>) => void;
  onSortDirectionChange: (sortDirection: SortDirection) => void;
  onReset: () => void;
  onSave: () => void;
}

const ClusterMappingToolbar = ({
  filter,
  sortDirection,
  savingState,
  hasSaveError,
  isValid,
  isMappingChanged,
  onFilterChange,
  onSortDirectionChange,
  onReset,
  onSave,
}: ClusterMappingToolbarProps) => {
  const handleFilterHostsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      hostName: event.target.value,
    });
  };

  const handleFilterComponentsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      componentDisplayName: event.target.value,
    });
  };

  const handleHideEmptyChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ isHideEmpty: event.target.checked });
  };

  const handleOrderChange = () => {
    onSortDirectionChange(sortDirection === 'desc' ? 'asc' : 'desc');
  };

  const isSavingInProgress = savingState === 'in-progress';
  const isButtonsDisabledByState = isSavingInProgress || !isMappingChanged;
  const sortIconClassName = cn(s.clusterMappingToolbar__sortIcon, {
    [s.clusterMappingToolbar__sortIcon_desc]: sortDirection === 'desc',
  });

  return (
    <Panel className={s.clusterMappingToolbar} data-test="configuration-toolbar">
      <div className={s.clusterMappingToolbar__inputAndSwitches}>
        <SearchInput
          placeholder="Search hosts"
          value={filter.hostName}
          onChange={handleFilterHostsChange}
          className={s.clusterMappingToolbar__searchInput}
        />
        <SearchInput
          placeholder="Search components"
          value={filter.componentDisplayName}
          onChange={handleFilterComponentsChange}
          className={s.clusterMappingToolbar__searchInput}
        />
        <div className={s.clusterMappingToolbar__sortIconWrapper}>
          {/* eslint-disable-next-line prettier/prettier*/}
          <IconButton icon="arrow" size="medium" className={sortIconClassName} onClick={handleOrderChange} /> A - Z
          order
        </div>
        <Switch
          //
          size="small"
          isToggled={filter.isHideEmpty}
          onChange={handleHideEmptyChange}
          label="Hide empty"
        />
      </div>
      <ButtonGroup>
        <Button disabled={isButtonsDisabledByState} variant="secondary" onClick={onReset}>
          Reset
        </Button>
        <Button
          onClick={onSave}
          disabled={isButtonsDisabledByState || !isValid}
          hasError={hasSaveError}
          iconLeft={isSavingInProgress ? { name: 'g1-load', className: 'spin' } : undefined}
        >
          Save
        </Button>
      </ButtonGroup>
    </Panel>
  );
};

export default ClusterMappingToolbar;
