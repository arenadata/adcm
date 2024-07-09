import React from 'react';
import { Button, ButtonGroup, Switch, Panel, SearchInput } from '@uikit';
import s from './ClusterAnsibleSettingsToolbar.module.scss';
import { useConfigurationFormContext } from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContext.context';

interface ConfigurationToolbarProps {
  onSave: () => void;
  onRevert: () => void;
  isConfigChanged: boolean;
}

const ClusterAnsibleSettingsToolbar: React.FC<ConfigurationToolbarProps> = ({ onSave, onRevert, isConfigChanged }) => {
  const { filter, onFilterChange, isValid, areExpandedAll, handleChangeExpandedAll } = useConfigurationFormContext();

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ title: e.target.value });
  };

  return (
    <Panel className={s.configurationToolbar} data-test="configuration-toolbar">
      <SearchInput
        placeholder="Search input"
        value={filter.title}
        onChange={handleSearch}
        className={s.configurationToolbar__search}
      />

      <Switch isToggled={areExpandedAll} onChange={handleChangeExpandedAll} label="Expand content" />

      <ButtonGroup className={s.configurationToolbar__buttons}>
        <Button variant="secondary" onClick={onRevert} disabled={!isConfigChanged}>
          Revert
        </Button>
        <Button onClick={onSave} hasError={!isValid} disabled={!(isConfigChanged && isValid)}>
          Save
        </Button>
      </ButtonGroup>
    </Panel>
  );
};

export default ClusterAnsibleSettingsToolbar;
