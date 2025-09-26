import { useEffect } from 'react';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import type { AdcmActionProcessConfigurationStep } from '@models/adcm/wizard';
import { prepareConfigurationFromStepData } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditor.utils';
import ActionWizardConfigurationEditorToolbar from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorToolbar/ActionWizardConfigurationEditorToolbar';
import { useActionWizardConfigurationEditorContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorContextProvider/ActionWizardConfigurationEditorContext.context';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';

interface ActionWizardConfigurationEditorProps {
  step: AdcmActionProcessConfigurationStep;
}

const ActionWizardConfigurationEditor = ({ step }: ActionWizardConfigurationEditorProps) => {
  const { configuration, setConfiguration } = useActionWizardConfigurationEditorContext();
  const { setIsValid } = useActionWizardValidationContext();

  useEffect(() => {
    const preparedConfig = prepareConfigurationFromStepData(step.configuration);
    setConfiguration(preparedConfig);
  }, [step.configuration]);

  const onReset = () => {
    const configuration = prepareConfigurationFromStepData(step.configuration);
    setConfiguration(configuration);
    setIsValid(true);
  };

  return (
    <ConfigurationFormContextProvider>
      <ActionWizardConfigurationEditorToolbar onRevert={onReset} />
      <ConfigurationMain configuration={configuration} onChangeConfiguration={setConfiguration} />
    </ConfigurationFormContextProvider>
  );
};

export default ActionWizardConfigurationEditor;
