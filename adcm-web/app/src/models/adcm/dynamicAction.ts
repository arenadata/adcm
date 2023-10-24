import { AdcmMapping } from '@models/adcm/clusterMapping';
import { AdcmConfig, ConfigurationSchema } from '@models/adcm/configuration';

export enum AdcmHostComponentMapRuleAction {
  Add = 'add',
  Remove = 'remove',
}

interface AdcmHostComponentMapRule {
  action: AdcmHostComponentMapRuleAction;
  service: string;
  component: string;
}

export interface AdcmDynamicAction {
  id: number;
  name: string;
  displayName: string;
  startImpossibleReason: string;
}

export type AdcmDynamicActionConfiguration = Pick<AdcmConfig, 'adcmMeta'> & {
  configSchema: ConfigurationSchema;
};

export interface AdcmDynamicActionDetails {
  id: number;
  name: string;
  displayName: string;
  isAllowToTerminate: boolean;
  disclaimer: string;
  hostComponentMapRules: AdcmHostComponentMapRule[];
  configuration: AdcmDynamicActionConfiguration | null;
}

export interface AdcmDynamicActionRunConfig {
  hostComponentMap: AdcmMapping[];
  isVerbose: boolean;
  configuration: Pick<AdcmConfig, 'config' | 'adcmMeta'> | null;
}
