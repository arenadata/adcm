import type { AdcmHostComponentMapRuleAction, AdcmMappingComponent } from '@models/adcm';
import type { MappingActionRule } from './mapping.types';

export const getRulesForComponent = (
  rules: MappingActionRule[],
  component: AdcmMappingComponent,
): Set<AdcmHostComponentMapRuleAction> => {
  const allowedActions = new Set<AdcmHostComponentMapRuleAction>();
  for (const rule of rules) {
    if (rule.service === component.service.name && rule.component === component.name) {
      allowedActions.add(rule.operation);
    }
  }
  return allowedActions;
};
