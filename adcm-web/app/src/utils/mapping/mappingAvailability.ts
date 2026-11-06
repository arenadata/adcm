import type {
  MappingAvailability,
  MappingModel,
  ComponentHostRelations,
  MappingItemAvailability,
} from './mapping.types';
import {
  getComponentLevelMapDeny,
  getPairRelation,
  isPairMapAllowed,
  isPairUnmapAllowed,
} from './componentHostRelations';

export const isComponentEditable = (availability: MappingItemAvailability) =>
  !availability.notAvailableReason && (availability.canMap || availability.canUnmap);

export const computeMappingAvailability = (
  model: MappingModel,
  relations: ComponentHostRelations,
): MappingAvailability => {
  const componentsAvailability: MappingAvailability['components'] = {};
  const allHosts = model.hostsMapping.map((hostMapping) => hostMapping.host);

  for (const { component } of model.componentsMapping) {
    const notAvailableReason = getComponentLevelMapDeny(relations, component.id);

    if (notAvailableReason) {
      componentsAvailability[component.id] = {
        canMap: false,
        canUnmap: false,
        notAvailableReason,
      };
      continue;
    }

    let canMap = false;
    let canUnmap = false;

    for (const host of allHosts) {
      const pair = getPairRelation(relations, component.id, host.id);
      canMap = canMap || isPairMapAllowed(pair);
      canUnmap = canUnmap || isPairUnmapAllowed(pair);
      if (canMap && canUnmap) {
        break;
      }
    }

    componentsAvailability[component.id] = { canMap, canUnmap };
  }

  const servicesAvailability: MappingAvailability['services'] = {};
  for (const serviceMapping of model.servicesMapping) {
    const isEditable = serviceMapping.componentsMapping.some((componentMapping) => {
      const componentAvailability = componentsAvailability[componentMapping.component.id];
      return Boolean(componentAvailability && isComponentEditable(componentAvailability));
    });
    servicesAvailability[serviceMapping.service.id] = { isEditable };
  }

  const hostsAvailability: MappingAvailability['hosts'] = {};
  const allComponents = model.componentsMapping.map((componentMapping) => componentMapping.component);

  for (const hostMapping of model.hostsMapping) {
    let canMap = false;
    let canUnmap = false;

    for (const component of allComponents) {
      const pair = getPairRelation(relations, component.id, hostMapping.host.id);
      canMap = canMap || isPairMapAllowed(pair);
      canUnmap = canUnmap || isPairUnmapAllowed(pair);
      if (canMap && canUnmap) {
        break;
      }
    }

    hostsAvailability[hostMapping.host.id] = { canMap, canUnmap };
  }

  return {
    components: componentsAvailability,
    hosts: hostsAvailability,
    services: servicesAvailability,
  };
};
