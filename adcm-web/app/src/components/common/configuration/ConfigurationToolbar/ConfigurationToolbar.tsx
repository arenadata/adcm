import React from 'react';
import Panel from '@uikit/Panel/Panel';
import SearchInput from '@uikit/SearchInput/SearchInput';
import { ButtonGroup, Switch } from '@uikit';
import Button from '@uikit/Button/Button';
import s from './ConfigurationToolbar.module.scss';
import { useConfigurationFormContext } from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContext.context';

interface ConfigurationToolbarProps {
  onSave: () => void;
  onRevert: () => void;
  isViewDraft: boolean;
}

const ConfigurationToolbar: React.FC<ConfigurationToolbarProps> = ({ onSave, onRevert, isViewDraft }) => {
  const { filter, onFilterChange, isValid } = useConfigurationFormContext();

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ title: e.target.value });
  };
  const handleShowAdvanced = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ showAdvanced: e.target.checked });
  };

  return (
    <Panel className={s.configurationToolbar}>
      <SearchInput
        placeholder="Search input"
        value={filter.title}
        onChange={handleSearch}
        className={s.configurationToolbar__search}
      />

      <Switch isToggled={filter.showAdvanced} variant="blue" onChange={handleShowAdvanced} label="Show advanced" />

      <ButtonGroup className={s.configurationToolbar__buttons}>
        <Button variant="secondary" onClick={onRevert} disabled={!isViewDraft}>
          Revert
        </Button>
        <Button onClick={onSave} hasError={!isValid} disabled={!isValid}>
          Save
        </Button>
      </ButtonGroup>
    </Panel>
  );
};

export default ConfigurationToolbar;
