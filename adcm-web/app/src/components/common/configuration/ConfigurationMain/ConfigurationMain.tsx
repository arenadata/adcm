import React from 'react';
import { ConfigurationEditor } from '@uikit';
import { AdcmConfiguration, ConfigurationData, ConfigurationAttributes } from '@models/adcm';
import { useConfigurationFormContext } from '../ConfigurationFormContext/ConfigurationFormContext.context';

interface ConfigurationMainProps {
  configuration: AdcmConfiguration | null;
  onChangeConfiguration: (configuration: AdcmConfiguration) => void;
  isLoading?: boolean;
}

const ConfigurationMain: React.FC<ConfigurationMainProps> = ({ configuration, onChangeConfiguration }) => {
  const { filter, onChangeIsValid } = useConfigurationFormContext();

  if (configuration === null) return null;

  const { configurationData, attributes, schema } = configuration;

  const handleChangeConfigurationData = (configurationData: ConfigurationData) => {
    onChangeConfiguration({
      configurationData,
      attributes,
      schema,
    });
  };

  const handleChangeAttributes = (attributes: ConfigurationAttributes) => {
    onChangeConfiguration({
      configurationData,
      attributes,
      schema,
    });
  };

  return (
    <ConfigurationEditor
      configuration={configurationData}
      attributes={attributes}
      schema={schema}
      filter={filter}
      onConfigurationChange={handleChangeConfigurationData}
      onAttributesChange={handleChangeAttributes}
      onChangeIsValid={onChangeIsValid}
    />
  );
};
export default ConfigurationMain;
