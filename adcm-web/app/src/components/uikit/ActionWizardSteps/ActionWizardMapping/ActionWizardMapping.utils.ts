import type {
  AdcmHostComponentMapRuleAction,
  AdcmMapping,
  AdcmMappingComponent,
  AdcmMappingComponentService,
} from '@models/adcm';
import type { AdcmActionProcessMappingStepRules, Delta } from '@models/adcm/wizard';
import type { ComponentMapping, ServiceMapping } from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import { sortBy } from '@utils/arrayUtils.ts';
import { componentsMappingSortByName } from '@pages/cluster/ClusterMapping/ClusterMapping.utils.ts';
import type { SortDirection } from '@models/table.ts';

const getKey = (item: AdcmMapping) => `${item.hostId}-${item.componentId}`;

export const applyMappingDelta = (currentMapping: AdcmMapping[], delta: Delta | null): AdcmMapping[] => {
  if (!delta) return currentMapping;
  const { add = [], remove = [] } = delta;
  const map = new Map<string, AdcmMapping>();
  let maxId = 0;

  for (const item of currentMapping) {
    const key = getKey(item);
    map.set(key, item);
    maxId = Math.max(maxId, item.id ?? 0);
  }

  for (const item of remove) {
    map.delete(getKey(item));
  }

  let nextId = maxId + 1;
  for (const item of add) {
    const key = getKey(item);
    if (!map.has(key)) {
      map.set(key, { id: nextId++, hostId: item.hostId, componentId: item.componentId });
    }
  }

  return Array.from(map.values());
};

export const getComponentMapActions = (
  rules: { operation: AdcmHostComponentMapRuleAction; component: string; service: string }[],
  service: AdcmMappingComponentService,
  component: AdcmMappingComponent,
) => {
  const result = new Set<AdcmHostComponentMapRuleAction>();

  for (const rule of rules) {
    if (rule.service === service.name && rule.component === component.name) {
      result.add(rule.operation);
    }
  }

  return result;
};

interface ComponentsMappingFnPayload {
  componentsMapping: ComponentMapping[];
  rules: AdcmActionProcessMappingStepRules[];
  service: AdcmMappingComponentService;
}

const extendActionWizardComponentMapping = ({ componentsMapping, rules, service }: ComponentsMappingFnPayload) => {
  return componentsMapping.map((componentMapping) => {
    const component = componentMapping.component;
    const allowActions = getComponentMapActions(rules, service, component);

    return {
      ...componentMapping,
      allowedActions: allowActions,
    };
  });
};

export const sortExtendedActionWizardComponentMapping = (
  { componentsMapping, rules, service }: ComponentsMappingFnPayload,
  sortDirection: SortDirection = 'asc',
) => {
  const extendedMapping = extendActionWizardComponentMapping({ componentsMapping, rules, service });

  const result = sortBy(extendedMapping, [
    (a, b) => b.allowedActions.size - a.allowedActions.size,
    (a, b) => componentsMappingSortByName(a.component, b.component),
  ]);

  if (sortDirection === 'desc') {
    result.reverse();
  }

  return result;
};

export const sortExtendedActionWizardServicesMapping = (
  servicesMapping: ServiceMapping[],
  rules: AdcmActionProcessMappingStepRules[],
  sortDirection: SortDirection = 'asc',
) => {
  const extendedMapping = servicesMapping.map((serviceMapping) => {
    const { service, componentsMapping } = serviceMapping;
    const newComponentsMapping = sortExtendedActionWizardComponentMapping(
      { componentsMapping, rules, service },
      sortDirection,
    );

    return {
      ...serviceMapping,
      service,
      componentsMapping: newComponentsMapping,
      isAllowedActions: newComponentsMapping.some(({ allowedActions }) => allowedActions.size > 0),
    };
  });

  const result = sortBy(extendedMapping, [
    (a, b) => Number(b.isAllowedActions) - Number(a.isAllowedActions),
    (a, b) => a.service.displayName.localeCompare(b.service.displayName),
  ]);

  if (sortDirection === 'desc') {
    result.reverse();
  }

  return result;
};
