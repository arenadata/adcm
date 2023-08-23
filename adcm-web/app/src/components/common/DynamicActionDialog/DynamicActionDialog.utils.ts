import { DynamicActionType } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';

export const getDynamicActionTypes = (actionDetails: AdcmDynamicActionDetails): DynamicActionType[] => {
  if (actionDetails.disclaimer) return [DynamicActionType.Confirm];

  const res = [] as DynamicActionType[];
  // TODO: configSchema will be changes, must change this condition in future.
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  if (actionDetails.configSchema?.fields?.length > 0) {
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

export const getDefaultConfigSchemaRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'config'> => ({
  config: {},
});

export const getDefaultVerboseRunConfig = (): Pick<AdcmDynamicActionRunConfig, 'isVerbose'> => ({
  isVerbose: false,
});

export const getDefaultRunConfig = (): AdcmDynamicActionRunConfig => ({
  ...getDefaultHostMappingRunConfig(),
  ...getDefaultConfigSchemaRunConfig(),
  ...getDefaultVerboseRunConfig(),
});
