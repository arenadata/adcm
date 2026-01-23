import {
  type AdcmDynamicActionDetails,
  AdcmHostComponentMapRuleAction,
  type AdcmHostShortView,
  AdcmMaintenanceMode,
  type AdcmMappingComponent,
  type AdcmMappingComponentService,
  type HostId,
} from '@models/adcm';
import type { ComponentAvailabilityErrors, ServiceMapping } from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import { sortBy } from '@utils/arrayUtils.ts';
import { componentsMappingSortByName } from '@pages/cluster/ClusterMapping/ClusterMapping.utils.ts';

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

export const checkComponentActionsMappingAvailability = (
  _component: AdcmMappingComponent,
  allowActions: Set<AdcmHostComponentMapRuleAction>,
): ComponentAvailabilityErrors => {
  const result: ComponentAvailabilityErrors = {};

  if (allowActions.size === 0) {
    result.componentNotAvailableError = 'Mapping is not allowed in action configuration';
  }

  return result;
};

export const checkHostActionsMappingAvailability = (
  host: AdcmHostShortView,
  allowActions: Set<AdcmHostComponentMapRuleAction> = new Set([
    AdcmHostComponentMapRuleAction.Add,
    AdcmHostComponentMapRuleAction.Remove,
  ]),
  initiallyMappedHosts: Set<HostId> = new Set(),
): string | undefined => {
  // always allow revert removable INCLUDES to initial hosts
  if (initiallyMappedHosts.has(host.id)) return undefined;

  if (!allowActions.has(AdcmHostComponentMapRuleAction.Add)) {
    return 'Adding host is not allowed in the action configuration';
  }

  if (host.maintenanceMode !== AdcmMaintenanceMode.Off) {
    return 'Maintenance mode on the host must be Off';
  }

  return undefined;
};

export const checkHostActionsUnmappingAvailability = (
  host: AdcmHostShortView,
  allowActions: Set<AdcmHostComponentMapRuleAction> = new Set([
    AdcmHostComponentMapRuleAction.Add,
    AdcmHostComponentMapRuleAction.Remove,
  ]),
  initiallyMappedHosts: Set<HostId> = new Set(),
): string | undefined => {
  // always allow revert appendable NOT includes to initial hosts
  if (!initiallyMappedHosts.has(host.id)) return undefined;

  if (!allowActions.has(AdcmHostComponentMapRuleAction.Remove)) {
    return 'Removing host is not allowed in the action configuration';
  }

  return undefined;
};

const extendComponentsMapping = (serviceMapping: ServiceMapping[], actionDetails: AdcmDynamicActionDetails) => {
  return serviceMapping.flatMap(({ service, componentsMapping }) =>
    componentsMapping.map((componentMapping) => {
      const component = componentMapping.component;
      const allowActions = getComponentMapActions(actionDetails, service, component);

      return {
        ...componentMapping,
        allowedActions: allowActions,
      };
    }),
  );
};

export const sortExtendedComponentsMapping = (
  serviceMapping: ServiceMapping[],
  actionDetails: AdcmDynamicActionDetails,
) => {
  const extendedMapping = extendComponentsMapping(serviceMapping, actionDetails);

  return sortBy(extendedMapping, [
    (a, b) => b.allowedActions.size - a.allowedActions.size,
    (a, b) => componentsMappingSortByName(a.component, b.component),
  ]);
};
