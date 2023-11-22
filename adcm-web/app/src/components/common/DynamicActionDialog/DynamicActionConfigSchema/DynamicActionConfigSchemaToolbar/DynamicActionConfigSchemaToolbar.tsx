import React from 'react';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';
import { Button, ButtonGroup, SearchInput, Switch } from '@uikit';
import ToolbarPanel from '@uikit/ToolbarPanel/ToolbarPanel';
import { useConfigurationFormContext } from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContext.context';

interface DynamicActionConfigSchemaToolbarProps {
  onSubmit: () => void;
  onCancel: () => void;
  onReset: () => void;
  submitLabel: string;
}

const DynamicActionConfigSchemaToolbar: React.FC<DynamicActionConfigSchemaToolbarProps> = ({
  onReset,
  onSubmit,
  onCancel,
  submitLabel,
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
        <Button onClick={onSubmit} hasError={!isValid} disabled={!isValid}>
          {submitLabel}
        </Button>
      </ButtonGroup>
    </ToolbarPanel>
  );
};
export default DynamicActionConfigSchemaToolbar;
