import { generateJsonSchemaDefaults } from '@utils/jsonSchema/JsonSchemaValidationService';
import type { AdcmWizardConfiguration } from '@models/adcm/wizard';
import type { AdcmConfiguration, ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';

export const prepareConfigurationFromStepData = (configuration: AdcmWizardConfiguration): AdcmConfiguration | null => {
  if (!configuration) {
    return null;
  }

  return {
    configurationData:
      configuration.config ?? generateJsonSchemaDefaults<ConfigurationData>(configuration.configSchema) ?? {},
    schema: configuration.configSchema as ConfigurationSchema,
    attributes: (configuration.adcmMeta || {}) as ConfigurationAttributes,
  };
};
