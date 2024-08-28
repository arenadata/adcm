import React from 'react';
import { Button, ButtonGroup, SearchInput, Switch, ToolbarPanel } from '@uikit';
import { useConfigurationFormContext } from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContext.context';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';

interface DynamicActionConfigSchemaToolbarProps {
  onNext: () => void;
  onCancel: () => void;
  onReset: () => void;
}

const DynamicActionConfigSchemaToolbar: React.FC<DynamicActionConfigSchemaToolbarProps> = ({
  onReset,
  onNext,
  onCancel,
}) => {
  const { filter, onFilterChange, isValid, areExpandedAll, handleChangeExpandedAll } = useConfigurationFormContext();

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ title: e.target.value });
  };

  const handleShowAdvanced = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ showAdvanced: e.target.checked });
  };

  return (
    <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
      <SearchInput placeholder="Search input" value={filter.title} onChange={handleSearch} />

      <Switch isToggled={areExpandedAll} onChange={handleChangeExpandedAll} label="Expand content" />
      <Switch isToggled={filter.showAdvanced} variant="blue" onChange={handleShowAdvanced} label="Show advanced" />

      <ButtonGroup>
        <Button variant="tertiary" iconLeft="g1-return" onClick={onReset} />
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button onClick={onNext} hasError={!isValid} disabled={!isValid}>
          Next
        </Button>
      </ButtonGroup>
    </ToolbarPanel>
  );
};
export default DynamicActionConfigSchemaToolbar;
