import type { AdcmHostComponentMapRuleAction, AdcmMappingComponent, AdcmMappingComponentService } from '@models/adcm';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';
import type { ComponentMapping, ServiceMapping } from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import { sortBy } from '@utils/arrayUtils.ts';
import { componentsMappingSortByName } from '@pages/cluster/ClusterMapping/ClusterMapping.utils.ts';
import type { SortDirection } from '@models/table.ts';

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
