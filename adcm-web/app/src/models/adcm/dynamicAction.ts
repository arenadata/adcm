import { AdcmMapping } from '@models/adcm/clusterMapping';

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

export interface AdcmDynamicActionDetails {
  id: number;
  name: string;
  displayName: string;
  isAllowToTerminate: boolean;
  disclaimer: string;
  hostComponentMapRules: AdcmHostComponentMapRule[];
  // TODO: change type after implement configSchema
  configSchema: object;
}

export interface AdcmDynamicActionRunConfig {
  hostComponentMap: AdcmMapping[];
  // TODO: change type after implement configSchema
  config: object;
  isVerbose: boolean;
}
