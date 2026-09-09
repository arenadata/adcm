import type React from 'react';
import { ConfigurationEditor } from '@uikit';
import type { AdcmConfiguration, ConfigurationData, ConfigurationAttributes } from '@models/adcm';
import { useConfigurationFormContext } from '../ConfigurationFormContext/ConfigurationFormContext.context';
import { generateJsonSchemaDefaults } from '@utils/jsonSchema/JsonSchemaValidationService';

interface ConfigurationMainProps {
  configuration: AdcmConfiguration | null;
  onChangeConfiguration: (configuration: AdcmConfiguration) => void;
  isLoading?: boolean;
  isReadOnly?: boolean;
}

const getCorrectConfigurationData = (configuration: AdcmConfiguration): ConfigurationData => {
  const { configurationData, schema } = configuration;

  if (Object.keys(configurationData).length > 0) {
    return configurationData;
  }
  return generateJsonSchemaDefaults<ConfigurationData>(schema) ?? {};
};

const ConfigurationMain: React.FC<ConfigurationMainProps> = ({
  configuration,
  onChangeConfiguration,
  isReadOnly = false,
}) => {
  const { filter, areExpandedAll, onChangeIsValid } = useConfigurationFormContext();

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

  const handleChangeConfigurationAndAttributes = (
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
  ) => {
    onChangeConfiguration({
      configurationData,
      attributes,
      schema,
    });
  };

  return (
    <ConfigurationEditor
      configuration={getCorrectConfigurationData(configuration)}
      attributes={attributes}
      schema={schema}
      filter={filter}
      areExpandedAll={areExpandedAll}
      onConfigurationChange={handleChangeConfigurationData}
      onAttributesChange={handleChangeAttributes}
      onConfigurationAndAttributesChange={handleChangeConfigurationAndAttributes}
      onChangeIsValid={onChangeIsValid}
      isReadOnly={isReadOnly}
    />
  );
};
export default ConfigurationMain;
