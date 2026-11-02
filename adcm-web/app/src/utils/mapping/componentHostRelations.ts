import {
  AdcmEntitySystemState,
  AdcmHostComponentMapRuleAction,
  AdcmMaintenanceMode,
  type AdcmHostShortView,
  type AdcmMapping,
  type AdcmMappingComponent,
  type ComponentId,
  type HostId,
} from '@models/adcm';
import { getRulesForComponent } from './mappingRules';
import type { ComponentHostRelations, MappingRelationsPolicy, PairKey, PairRelation } from './mapping.types';

export const SERVICE_NOT_CREATED =
  'Service of this component must have "Created" state. Maintenance mode on the components must be Off';
export const HOST_MM = 'Maintenance mode on the host must be Off';
export const MAPPING_NOT_ALLOWED = 'Mapping is not allowed in action configuration';
export const ADD_NOT_ALLOWED = 'Adding host is not allowed in the action configuration';
export const REMOVE_NOT_ALLOWED = 'Removing host is not allowed in the action configuration';

const CLUSTER_ACTIONS = new Set([AdcmHostComponentMapRuleAction.Add, AdcmHostComponentMapRuleAction.Remove]);

export const makePairKey = (componentId: ComponentId, hostId: HostId): PairKey => `${componentId}_${hostId}`;

export const emptyPairRelation = (): PairRelation => ({
  map: { denyReasons: [] },
  unmap: { denyReasons: [] },
});

const buildBaselineHostsByComponent = (baselinePairs: AdcmMapping[]): Map<ComponentId, Set<HostId>> => {
  const result = new Map<ComponentId, Set<HostId>>();
  for (const pair of baselinePairs) {
    let hosts = result.get(pair.componentId);
    if (!hosts) {
      hosts = new Set();
      result.set(pair.componentId, hosts);
    }
    hosts.add(pair.hostId);
  }
  return result;
};

const applyClusterPairDenies = (
  relation: PairRelation,
  isServiceNotCreated: boolean,
  host: AdcmHostShortView,
  isBaselineMapped: boolean,
) => {
  if (isServiceNotCreated) {
    relation.map.denyReasons.push(SERVICE_NOT_CREATED);
    relation.unmap.denyReasons.push(SERVICE_NOT_CREATED);
  }

  if (!isBaselineMapped && host.maintenanceMode !== AdcmMaintenanceMode.Off) {
    relation.map.denyReasons.push(HOST_MM);
  }
};

const applyActionRulesPairDenies = (
  relation: PairRelation,
  host: AdcmHostShortView,
  isBaselineMapped: boolean,
  hasNoRules: boolean,
  canAdd: boolean,
  canRemove: boolean,
) => {
  if (hasNoRules) {
    relation.map.denyReasons.push(MAPPING_NOT_ALLOWED);
    relation.unmap.denyReasons.push(MAPPING_NOT_ALLOWED);
    return;
  }

  if (!isBaselineMapped) {
    if (!canAdd) {
      relation.map.denyReasons.push(ADD_NOT_ALLOWED);
    }
    if (host.maintenanceMode !== AdcmMaintenanceMode.Off) {
      relation.map.denyReasons.push(HOST_MM);
    }
    return;
  }

  if (!canRemove) {
    relation.unmap.denyReasons.push(REMOVE_NOT_ALLOWED);
  }
};

const resolveComponentLevelDeny = (
  policy: MappingRelationsPolicy,
  isServiceNotCreated: boolean,
  hasNoRules: boolean,
): string | undefined => {
  if (policy.type === 'cluster') {
    return isServiceNotCreated ? SERVICE_NOT_CREATED : undefined;
  }
  return hasNoRules ? MAPPING_NOT_ALLOWED : undefined;
};

export const buildComponentHostRelations = (input: {
  hosts: AdcmHostShortView[];
  components: AdcmMappingComponent[];
  baselinePairs: AdcmMapping[];
  policy: MappingRelationsPolicy;
}): ComponentHostRelations => {
  const pairs: ComponentHostRelations['pairs'] = new Map();
  const componentLevelDenies: ComponentHostRelations['componentLevelDenies'] = new Map();
  const baselineHostsByComponent = buildBaselineHostsByComponent(input.baselinePairs);

  for (const component of input.components) {
    const baselineHosts = baselineHostsByComponent.get(component.id) ?? new Set<HostId>();
    const isServiceNotCreated = component.service.state !== AdcmEntitySystemState.Created;
    const allowedActions =
      input.policy.type === 'cluster' ? CLUSTER_ACTIONS : getRulesForComponent(input.policy.rules, component);
    const hasNoRules = allowedActions.size === 0;
    const canAdd = allowedActions.has(AdcmHostComponentMapRuleAction.Add);
    const canRemove = allowedActions.has(AdcmHostComponentMapRuleAction.Remove);

    const levelDeny = resolveComponentLevelDeny(input.policy, isServiceNotCreated, hasNoRules);
    if (levelDeny) {
      componentLevelDenies.set(component.id, levelDeny);
    }

    for (const host of input.hosts) {
      const relation = emptyPairRelation();
      const isBaselineMapped = baselineHosts.has(host.id);

      if (input.policy.type === 'cluster') {
        applyClusterPairDenies(relation, isServiceNotCreated, host, isBaselineMapped);
      } else {
        applyActionRulesPairDenies(relation, host, isBaselineMapped, hasNoRules, canAdd, canRemove);
      }

      pairs.set(makePairKey(component.id, host.id), relation);
    }
  }

  return { pairs, componentLevelDenies };
};

export const getPairRelation = (
  relations: ComponentHostRelations,
  componentId: ComponentId,
  hostId: HostId,
): PairRelation => {
  const relation = relations.pairs.get(makePairKey(componentId, hostId));
  if (!relation) {
    throw new Error(`Missing ComponentHostRelations entry for component ${componentId} and host ${hostId}`);
  }
  return relation;
};

export const isPairMapAllowed = (relation: PairRelation): boolean => relation.map.denyReasons.length === 0;

export const isPairUnmapAllowed = (relation: PairRelation): boolean => relation.unmap.denyReasons.length === 0;

export const firstDenyReason = (denyReasons: string[]): string | undefined => denyReasons[0];

export const getComponentLevelMapDeny = (
  relations: ComponentHostRelations,
  componentId: ComponentId,
): string | undefined => relations.componentLevelDenies.get(componentId);

export const getHostMapBlockedReason = (
  relations: ComponentHostRelations,
  hostId: HostId,
  componentIds: ComponentId[],
  mappedComponentCount = 0,
): string | undefined => {
  if (mappedComponentCount > 0 || componentIds.length === 0) {
    return undefined;
  }

  let firstDeny: string | undefined;
  for (const componentId of componentIds) {
    const deny = firstDenyReason(getPairRelation(relations, componentId, hostId).map.denyReasons);
    if (!deny) {
      return undefined;
    }
    firstDeny ??= deny;
  }
  return firstDeny;
};
