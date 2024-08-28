import type {
  AdcmDynamicActionDetails,
  AdcmHostComponentMapRuleAction,
  AdcmMapping,
  AdcmMappingComponent,
  AdcmMappingComponentService,
} from '@models/adcm';
import type { DisabledComponentsMappings } from '@pages/cluster/ClusterMapping/ClusterMapping.types';

export const getComponentMapActions = (
  actionDetails: AdcmDynamicActionDetails,
  service: AdcmMappingComponentService,
  component: AdcmMappingComponent,
) => {
  const result = new Set<AdcmHostComponentMapRuleAction>();

  for (const rule of actionDetails.hostComponentMapRules) {
    if (rule.service === service.name && rule.component === component.name) {
      result.add(rule.action);
    }
  }

  return result;
};

export const getDisabledMappings = (mapping: AdcmMapping[]) => {
  const result: DisabledComponentsMappings = {};

  for (const m of mapping) {
    if (result[m.componentId] === undefined) {
      result[m.componentId] = new Set();
    }

    result[m.componentId].add(m.hostId);
  }

  return result;
};
