import { useState } from 'react';
import { prepareConfigurationFromActionDetails } from '@commonComponents/DynamicActionDialog/DynamicActionDialog.utils';
import DynamicActionConfigSchemaToolbar from './DynamicActionConfigSchemaToolbar/DynamicActionConfigSchemaToolbar';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import type { AdcmConfiguration, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';

interface DynamicActionConfigSchemaProps {
  actionDetails: AdcmDynamicActionDetails;
  configuration?: AdcmDynamicActionRunConfig['configuration'] | null;
  onNext: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

const DynamicActionConfigSchema = ({
  actionDetails,
  onNext,
  onCancel,
  configuration: runConfiguration,
}: DynamicActionConfigSchemaProps) => {
  const [localConfiguration, setLocalConfiguration] = useState<AdcmConfiguration | null>(() => {
    const configuration = prepareConfigurationFromActionDetails(actionDetails);
    if (configuration === null) return null;

    return {
      configurationData: runConfiguration?.config ?? configuration.configurationData,
      attributes: runConfiguration?.adcmMeta ?? configuration.attributes,
      schema: configuration.schema,
    };
  });

  const onReset = () => {
    const configuration = prepareConfigurationFromActionDetails(actionDetails);
    setLocalConfiguration(configuration);
  };

  const handleNext = () => {
    if (localConfiguration) {
      onNext({
        configuration: { config: localConfiguration.configurationData, adcmMeta: localConfiguration.attributes },
      });
    }
  };

  return (
    <div>
      <ConfigurationFormContextProvider>
        <DynamicActionConfigSchemaToolbar onCancel={onCancel} onReset={onReset} onNext={handleNext} />
        <ConfigurationMain configuration={localConfiguration} onChangeConfiguration={setLocalConfiguration} />
      </ConfigurationFormContextProvider>
    </div>
  );
};

export default DynamicActionConfigSchema;
