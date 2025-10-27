import type React from 'react';
import { useEffect } from 'react';
import Panel from '@uikit/Panel/Panel';
import SearchInput from '@uikit/SearchInput/SearchInput';
import { Switch } from '@uikit';
import s from './ActionWizardConfigurationEditorToolbar.module.scss';
import { useConfigurationFormContext } from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContext.context';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';

const ActionWizardConfigurationEditorToolbar: React.FC = () => {
  const { filter, onFilterChange, areExpandedAll, handleChangeExpandedAll } = useConfigurationFormContext();
  const { isValid } = useConfigurationFormContext();
  const { setIsValid } = useActionWizardValidationContext();

  // Sync isValid to the wizard context
  useEffect(() => {
    setIsValid(isValid);
  }, [isValid, setIsValid]);

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ title: e.target.value });
  };
  const handleShowAdvanced = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({ showAdvanced: e.target.checked });
  };

  return (
    <Panel className={s.actionWizardConfigurationEditorToolbar} data-test="configuration-toolbar">
      <SearchInput
        placeholder="Search"
        value={filter.title}
        onChange={handleSearch}
        className={s.actionWizardConfigurationEditorToolbar__search}
      />
      <Switch isToggled={areExpandedAll} onChange={handleChangeExpandedAll} label="Expand content" />
      <Switch isToggled={filter.showAdvanced} variant="blue" onChange={handleShowAdvanced} label="Advanced" />
    </Panel>
  );
};

export default ActionWizardConfigurationEditorToolbar;
