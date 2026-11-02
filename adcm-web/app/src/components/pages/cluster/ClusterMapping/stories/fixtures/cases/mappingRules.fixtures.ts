import { AdcmHostComponentMapRuleAction } from '@models/adcm';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';

export const mappingRule = (
  operation: AdcmHostComponentMapRuleAction,
  component: string,
  service: string,
): AdcmActionProcessMappingStepRules => ({
  operation,
  component,
  service,
  description: '',
  required: false,
});

export const addOnlyZkServerRules: AdcmActionProcessMappingStepRules[] = [
  mappingRule(AdcmHostComponentMapRuleAction.Add, 'zk_server', 'zookeeper'),
];

export const removeOnlyZkServerRules: AdcmActionProcessMappingStepRules[] = [
  mappingRule(AdcmHostComponentMapRuleAction.Remove, 'zk_server', 'zookeeper'),
];

export const addRemoveZkServerRules: AdcmActionProcessMappingStepRules[] = [
  mappingRule(AdcmHostComponentMapRuleAction.Add, 'zk_server', 'zookeeper'),
  mappingRule(AdcmHostComponentMapRuleAction.Remove, 'zk_server', 'zookeeper'),
];

export const emptyRules: AdcmActionProcessMappingStepRules[] = [];
