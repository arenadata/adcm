import React from 'react';
import { Button, ButtonGroup, Panel, SearchInput, Switch } from '@uikit';
import { MappingFilter } from '../ClusterMapping.types';
import { ActionState } from '@models/loadState';
import s from './ClusterMappingToolbar.module.scss';

export interface ClusterMappingToolbarProps {
  isHostsPreviewMode: boolean;
  filter: MappingFilter;
  savingState: ActionState;
  hasSaveError: boolean;
  isValid: boolean;
  isMappingChanged: boolean;
  onHostsPreviewModeChange: (isHostsPreviewMode: boolean) => void;
  onFilterChange: (filter: Partial<MappingFilter>) => void;
  onReset: () => void;
  onSave: () => void;
}

const ClusterMappingToolbar = ({
  isHostsPreviewMode,
  filter,
  savingState,
  hasSaveError,
  isValid,
  isMappingChanged,
  onHostsPreviewModeChange,
  onFilterChange,
  onReset,
  onSave,
}: ClusterMappingToolbarProps) => {
  const handleFilterHostsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      componentDisplayName: '',
      hostName: event.target.value,
    });
  };

  const handleFilterComponentsChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      componentDisplayName: event.target.value,
      hostName: '',
    });
  };

  const handleHideEmptyChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ isHideEmpty: event.target.checked });
  };

  const handleHostsPreviewModeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onHostsPreviewModeChange(event.target.checked);
  };

  const isSavingInProgress = savingState === 'in-progress';
  const isButtonsDisabledByState = isSavingInProgress || !isMappingChanged;

  return (
    <Panel className={s.clusterMappingToolbar} data-test="configuration-toolbar">
      <div className={s.clusterMappingToolbar__inputAndSwitches}>
        {isHostsPreviewMode ? (
          <SearchInput
            placeholder="Search components"
            value={filter.componentDisplayName}
            onChange={handleFilterComponentsChange}
            className={s.clusterMappingToolbar__searchInput}
          />
        ) : (
          <SearchInput
            placeholder="Search hosts"
            value={filter.hostName}
            onChange={handleFilterHostsChange}
            className={s.clusterMappingToolbar__searchInput}
          />
        )}

        <Switch
          //
          size="small"
          isToggled={filter.isHideEmpty}
          onChange={handleHideEmptyChange}
          label="Hide empty"
        />
        <Switch
          size="small"
          isToggled={isHostsPreviewMode}
          onChange={handleHostsPreviewModeChange}
          label="Hosts preview mode"
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
