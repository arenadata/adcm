import {
  type AdcmDynamicActionDetails,
  AdcmHostComponentMapRuleAction,
  type AdcmHostShortView,
  AdcmMaintenanceMode,
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
  return result;
};

export const checkHostActionsMappingAvailability = (
  host: AdcmHostShortView,
  allowActions: Set<AdcmHostComponentMapRuleAction>,
  initiallyMappedHosts: Set<HostId> = new Set(),
): string | undefined => {
  // always allow revert removable INCLUDES to initial hosts
  if (initiallyMappedHosts.has(host.id)) return undefined;

  if (host.maintenanceMode !== AdcmMaintenanceMode.Off) {
    return 'Maintenance mode on the host must be Off';
  }

  if (!allowActions.has(AdcmHostComponentMapRuleAction.Add)) {
    return 'Adding host is not allowed in the action configuration';
  }

  return undefined;
};

export const checkHostActionsUnmappingAvailability = (
  host: AdcmHostShortView,
  allowActions: Set<AdcmHostComponentMapRuleAction>,
  initiallyMappedHosts: Set<HostId> = new Set(),
): string | undefined => {
  // always allow revert appendable NOT includes to initial hosts
  if (!initiallyMappedHosts.has(host.id)) return undefined;

  if (!allowActions.has(AdcmHostComponentMapRuleAction.Remove)) {
    return 'Removing host is not allowed in the action configuration';
  }

  return undefined;
};
