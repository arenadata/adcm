import { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';

export interface DynamicActionCommonOptions {
  actionDetails: AdcmDynamicActionDetails;
  onSubmit: (data: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

export enum DynamicActionType {
  Confirm = 'confirm',
  ConfigSchema = 'configSchema',
  HostComponentMapping = 'hostComponentMapping',
}
