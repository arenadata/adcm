import type { MappingFilter } from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import type { SortDirection } from '@models/table';
import { Panel, SearchInput, Switch } from '@uikit';
import s from './ActionWizardMappingToolbar.module.scss';

export interface ActionWizardMappingToolbarProps {
  filter: MappingFilter;
  sortDirection: SortDirection;
  isHostsPreviewMode: boolean;
  onHostModeChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onFilterChange: (filter: Partial<MappingFilter>) => void;
  onSortDirectionChange: (sortDirection: SortDirection) => void;
}

const ActionWizardMappingToolbar = ({
  filter,
  // sortDirection,
  isHostsPreviewMode = false,
  onHostModeChange,
  onFilterChange,
  // onSortDirectionChange,
}: ActionWizardMappingToolbarProps) => {
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

  // const handleOrderChange = () => {
  //   onSortDirectionChange(sortDirection === 'desc' ? 'asc' : 'desc');
  // };
  //
  // const sortIconClassName = cn(s.actionWizardMappingToolbar__sortIcon, {
  //   [s.actionWizardMappingToolbar__sortIcon_desc]: sortDirection === 'desc',
  // });

  return (
    <Panel className={s.actionWizardMappingToolbar} data-test="configuration-toolbar">
      <div className={s.actionWizardMappingToolbar__inputAndSwitches}>
        <SearchInput
          placeholder="Search hosts"
          value={filter.hostName}
          onChange={handleFilterHostsChange}
          className={s.actionWizardMappingToolbar__searchInput}
        />
        <SearchInput
          placeholder="Search components"
          value={filter.componentDisplayName}
          onChange={handleFilterComponentsChange}
          className={s.actionWizardMappingToolbar__searchInput}
        />
        {false && (
          /* hiding switcher temporarly */
          <Switch
            className={s.hostsModeSwitch}
            size="small"
            isToggled={isHostsPreviewMode ?? false}
            onChange={onHostModeChange}
            label="Hosts mode"
          />
        )}
        {/*<div className={s.actionWizardMappingToolbar__sortIconWrapper}>
          <IconButton icon="arrow" size="medium" className={sortIconClassName} onClick={handleOrderChange} /> A - Z
          order
        </div>*/}
        <Switch
          //
          size="small"
          isToggled={filter.isHideEmpty}
          onChange={handleHideEmptyChange}
          label="Hide empty"
        />
      </div>
    </Panel>
  );
};

export default ActionWizardMappingToolbar;
