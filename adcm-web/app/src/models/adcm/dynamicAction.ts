import type { AdcmMapping } from './clusterMapping';
import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from './configuration';

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

export type AdcmDynamicActionConfiguration = {
  config: ConfigurationData;
  adcmMeta: ConfigurationAttributes;
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
  configuration: {
    config: ConfigurationData;
    adcmMeta: ConfigurationAttributes;
  } | null;
}

export type EntitiesDynamicActions = Record<number, AdcmDynamicAction[]>;
