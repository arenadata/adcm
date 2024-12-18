import {
  type AdcmDynamicActionDetails,
  AdcmHostComponentMapRuleAction,
  type AdcmHostShortView,
  type AdcmMapping,
  type AdcmMappingComponent,
  type AdcmMappingComponentService,
  type HostId,
} from '@models/adcm';
import type {
  ComponentAvailabilityErrors,
  InitiallyMappedHostsDictionary,
} from '@pages/cluster/ClusterMapping/ClusterMapping.types';

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

export const getInitiallyMappedHostsDictionary = (mapping: AdcmMapping[]) => {
  const result: InitiallyMappedHostsDictionary = {};

  for (const m of mapping) {
    if (result[m.componentId] === undefined) {
      result[m.componentId] = new Set();
    }

    result[m.componentId].add(m.hostId);
  }

  return result;
};

export const checkComponentActionsMappingAvailability = (
  _component: AdcmMappingComponent,
  allowActions: Set<AdcmHostComponentMapRuleAction>,
): ComponentAvailabilityErrors => {
  const result: ComponentAvailabilityErrors = {};

  result.componentNotAvailableError =
    allowActions.size === 0 ? 'Mapping is not allowed in action configuration' : result.componentNotAvailableError;
  result.addingHostsNotAllowedError = !allowActions.has(AdcmHostComponentMapRuleAction.Add)
    ? 'Adding hosts is not allowed in the action configuration'
    : undefined;
  result.removingHostsNotAllowedError = !allowActions.has(AdcmHostComponentMapRuleAction.Remove)
    ? 'Removing hosts is not allowed in the action configuration'
    : undefined;

  return result;
};

export const checkHostActionsUnmappingAvailability = (
  host: AdcmHostShortView,
  allowActions: Set<AdcmHostComponentMapRuleAction>,
  initiallyMappedHosts: Set<HostId> = new Set(),
): string | undefined => {
  const isDisabled = !allowActions.has(AdcmHostComponentMapRuleAction.Remove) && initiallyMappedHosts.has(host.id);
  if (isDisabled) return 'Removing host is not allowed in the action configuration';
};
