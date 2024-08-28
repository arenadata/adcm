import { DynamicActionStep } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import type {
  AdcmActionHostGroup,
  AdcmConfiguration,
  ConfigurationData,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm';
import { generateFromSchema } from '@utils/jsonSchema/jsonSchemaUtils';

export const getDynamicActionSteps = (
  actionDetails: AdcmDynamicActionDetails,
  actionHostsGroup: AdcmActionHostGroup | undefined,
): DynamicActionStep[] => {
  const steps = [] as DynamicActionStep[];

  if (actionHostsGroup) {
    steps.push(DynamicActionStep.AgreeActionHostsGroup);
  }

  if (actionDetails.configuration !== null) {
    steps.push(DynamicActionStep.ConfigSchema);
  }

  if (actionDetails.hostComponentMapRules.length > 0) {
    steps.push(DynamicActionStep.HostComponentMapping);
  }

  steps.push(DynamicActionStep.Confirm);
  return steps;
};

const getDefaultHostMappingRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'hostComponentMap'> => ({
  hostComponentMap: [],
});

const getDefaultConfigurationRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'configuration'> => ({
  configuration: null,
});

const getDefaultVerboseRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'isVerbose'> => ({
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
