import { DynamicActionType } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { AdcmConfiguration, ConfigurationData } from '@models/adcm';
import { generateFromSchema } from '@utils/jsonSchema/jsonSchemaUtils';

export const getDynamicActionTypes = (actionDetails: AdcmDynamicActionDetails): DynamicActionType[] => {
  const res = [] as DynamicActionType[];
  if (actionDetails.configuration !== null) {
    res.push(DynamicActionType.ConfigSchema);
  }

  if (actionDetails.hostComponentMapRules.length > 0) {
    res.push(DynamicActionType.HostComponentMapping);
  }

  if (res.length > 0) {
    return res;
  }

  // fallback for standard message 'Are you sure?'
  return [DynamicActionType.Confirm];
};

export const getDefaultHostMappingRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'hostComponentMap'> => ({
  hostComponentMap: [],
});

export const getDefaultConfigurationRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'configuration'> => ({
  configuration: null,
});

export const getDefaultVerboseRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'isVerbose'> => ({
  isVerbose: false,
});

export const getDefaultRunConfig = (): AdcmDynamicActionRunConfig => ({
  ...getDefaultHostMappingRunConfig(),
  ...getDefaultConfigurationRunConfig(),
  ...getDefaultVerboseRunConfig(),
});

export const prepareConfigurationFromActionDetails = (
  actionDetails: AdcmDynamicActionDetails,
): AdcmConfiguration | null => {
  if (actionDetails.configuration === null) {
    return null;
  }

  const { adcmMeta } = getDefaultConfigurationRunConfig().configuration ?? {};
  const configuration = {
    configurationData:
      actionDetails.configuration.config ??
      generateFromSchema<ConfigurationData>(actionDetails.configuration.configSchema) ??
      {},
    attributes: actionDetails.configuration.adcmMeta ?? adcmMeta ?? {},
    schema: actionDetails.configuration.configSchema,
  };

  return configuration;
};
