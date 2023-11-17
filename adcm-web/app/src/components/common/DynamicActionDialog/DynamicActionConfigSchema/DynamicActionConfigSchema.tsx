import React, { useState } from 'react';
import { DynamicActionCommonOptions } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import { prepareConfigurationFromActionDetails } from '@commonComponents/DynamicActionDialog/DynamicActionDialog.utils';
import DynamicActionConfigSchemaToolbar from './DynamicActionConfigSchemaToolbar/DynamicActionConfigSchemaToolbar';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import { AdcmConfiguration, AdcmDynamicActionRunConfig } from '@models/adcm';

interface DynamicActionConfigSchemaProps extends DynamicActionCommonOptions {
  submitLabel?: string;
  configuration?: AdcmDynamicActionRunConfig['configuration'] | null;
}

const DynamicActionConfigSchema: React.FC<DynamicActionConfigSchemaProps> = ({
  actionDetails,
  onSubmit,
  onCancel,
  submitLabel = 'Run',
  configuration: runConfiguration,
}) => {
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

  const handleSubmit = () => {
    if (localConfiguration) {
      onSubmit({
        configuration: { config: localConfiguration.configurationData, adcmMeta: localConfiguration.attributes },
      });
    }
  };

  return (
    <div>
      <ConfigurationFormContextProvider>
        <DynamicActionConfigSchemaToolbar
          onCancel={onCancel}
          submitLabel={submitLabel}
          onReset={onReset}
          onSubmit={handleSubmit}
        />
        <ConfigurationMain configuration={localConfiguration} onChangeConfiguration={setLocalConfiguration} />
      </ConfigurationFormContextProvider>
    </div>
  );
};

export default DynamicActionConfigSchema;
