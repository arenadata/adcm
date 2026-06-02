import { DynamicActionStep } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import type {
  AdcmActionHostGroup,
  AdcmConfiguration,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
  ConfigurationData,
} from '@models/adcm';
import { generateJsonSchemaDefaults } from '@utils/jsonSchema/JsonSchemaValidationService';

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

  steps.push(DynamicActionStep.RaisingConcerns);
  steps.push(DynamicActionStep.Confirm);
  return steps;
};

const getDefaultHostMappingRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'hostComponentMap'> => ({
  hostComponentMap: [],
});

const getDefaultConfigurationRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'configuration'> => ({
  configuration: null,
});

const getDefaultShouldBlockObjectConfig = (): Pick<AdcmDynamicActionRunConfig, 'shouldBlockObject'> => ({
  shouldBlockObject: true,
});

const getDefaultVerboseRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'isVerbose'> => ({
  isVerbose: false,
});

const getDefaultDescriptionConfig = (): Pick<AdcmDynamicActionRunConfig, 'description'> => ({
  description: '',
});

export const getDefaultRunConfig = (): AdcmDynamicActionRunConfig => ({
  ...getDefaultHostMappingRunConfig(),
  ...getDefaultConfigurationRunConfig(),
  ...getDefaultShouldBlockObjectConfig(),
  ...getDefaultVerboseRunConfig(),
  ...getDefaultDescriptionConfig(),
});

export const prepareConfigurationFromActionDetails = (
  actionDetails: AdcmDynamicActionDetails,
): AdcmConfiguration | null => {
  if (actionDetails.configuration === null) {
    return null;
  }

  const { adcmMeta } = getDefaultConfigurationRunConfig().configuration ?? {};

  return {
    configurationData:
      actionDetails.configuration.config ??
      generateJsonSchemaDefaults<ConfigurationData>(actionDetails.configuration.configSchema) ??
      {},
    attributes: actionDetails.configuration.adcmMeta ?? adcmMeta ?? {},
    schema: actionDetails.configuration.configSchema,
  };
};
