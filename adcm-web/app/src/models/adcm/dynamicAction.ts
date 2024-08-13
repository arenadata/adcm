import { AdcmMapping } from './clusterMapping';
import { AdcmConfig, ConfigurationSchema } from './configuration';

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

export type AdcmDynamicActionConfiguration = Pick<AdcmConfig, 'config' | 'adcmMeta'> & {
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

export type EntitiesDynamicActions = Record<number, AdcmDynamicAction[]>;
