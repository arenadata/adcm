import type {
  AdcmDynamicActionDetails,
  AdcmHostShortView,
  AdcmMappingComponent,
  AdcmMappingComponentService,
  HostId,
} from '@models/adcm';
import { AdcmHostComponentMapRuleAction, AdcmMaintenanceMode } from '@models/adcm';
import type { ComponentAvailabilityErrors, ServiceMapping } from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import { sortBy } from '@utils/arrayUtils.ts';
import { componentsMappingSortByName } from '@pages/cluster/ClusterMapping/ClusterMapping.utils.ts';
import {
  ADD_NOT_ALLOWED,
  HOST_MM,
  MAPPING_NOT_ALLOWED,
  REMOVE_NOT_ALLOWED,
} from '@utils/mapping/componentHostRelations';

type ActionDetailsWithMapRules = Pick<AdcmDynamicActionDetails, 'hostComponentMapRules'>;

export const getComponentMapActions = (
  actionDetails: ActionDetailsWithMapRules,
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
    result.componentNotAvailableError = MAPPING_NOT_ALLOWED;
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
    return ADD_NOT_ALLOWED;
  }

  if (host.maintenanceMode !== AdcmMaintenanceMode.Off) {
    return HOST_MM;
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
    return REMOVE_NOT_ALLOWED;
  }

  return undefined;
};

const extendComponentsMapping = (serviceMapping: ServiceMapping[], actionDetails: ActionDetailsWithMapRules) => {
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
  actionDetails: ActionDetailsWithMapRules,
) => {
  const extendedMapping = extendComponentsMapping(serviceMapping, actionDetails);

  return sortBy(extendedMapping, [
    (a, b) => b.allowedActions.size - a.allowedActions.size,
    (a, b) => componentsMappingSortByName(a.component, b.component),
  ]);
};
