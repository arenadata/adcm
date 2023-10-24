import React, { useCallback, useEffect, useState } from 'react';
import { DynamicActionCommonOptions } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import { getDefaultConfigurationRunConfig } from '@commonComponents/DynamicActionDialog/DynamicActionDialog.utils';
import DynamicActionConfigSchemaToolbar from '@commonComponents/DynamicActionDialog/DynamicActionConfigSchema/DynamicActionConfigSchemaToolbar/DynamicActionConfigSchemaToolbar';
import ConfigurationFormContextProvider from '@commonComponents/configuration/ConfigurationFormContext/ConfigurationFormContextProvider';
import ConfigurationMain from '@commonComponents/configuration/ConfigurationMain/ConfigurationMain';
import { AdcmConfiguration, ConfigurationData } from '@models/adcm';
import { generateFromSchema } from '@utils/jsonSchemaUtils';

interface DynamicActionConfigSchemaProps extends DynamicActionCommonOptions {
  submitLabel?: string;
}

const DynamicActionConfigSchema: React.FC<DynamicActionConfigSchemaProps> = ({
  actionDetails,
  onSubmit,
  onCancel,
  submitLabel = 'Run',
}) => {
  const [localConfiguration, setLocalConfiguration] = useState<AdcmConfiguration | null>(null);

  const handleResetClick = useCallback(() => {
    if (actionDetails.configuration === null) {
      setLocalConfiguration(null);
      return;
    }

    const { adcmMeta } = getDefaultConfigurationRunConfig().configuration ?? {};
    const configuration = {
      configurationData: generateFromSchema<ConfigurationData>(actionDetails.configuration.configSchema) ?? {},
      attributes: actionDetails.configuration.adcmMeta ?? adcmMeta ?? {},
      schema: actionDetails.configuration.configSchema,
    };

    setLocalConfiguration(configuration);
  }, [actionDetails, setLocalConfiguration]);

  useEffect(() => {
    handleResetClick();
  }, [handleResetClick]);

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
          onReset={handleResetClick}
          onSubmit={handleSubmit}
        />
        <ConfigurationMain configuration={localConfiguration} onChangeConfiguration={setLocalConfiguration} />
      </ConfigurationFormContextProvider>
    </div>
  );
};

export default DynamicActionConfigSchema;
