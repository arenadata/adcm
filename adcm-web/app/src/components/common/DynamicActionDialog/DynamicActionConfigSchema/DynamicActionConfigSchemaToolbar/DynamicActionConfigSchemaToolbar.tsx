import React from 'react';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';
import { Button, ButtonGroup, SearchInput } from '@uikit';
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
  const { filter, onFilterChange, isValid } = useConfigurationFormContext();

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ title: e.target.value });
  };

  return (
    <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
      <SearchInput placeholder="Search input" value={filter.title} onChange={handleSearch} />

      <ButtonGroup>
        <Button variant="secondary" iconLeft="g1-return" onClick={onReset} />
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
