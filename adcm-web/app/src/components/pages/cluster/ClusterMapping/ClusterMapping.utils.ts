import {
  type AdcmComponentConstraint,
  AdcmEntitySystemState,
  type AdcmHostShortView,
  AdcmMaintenanceMode,
  type AdcmMapping,
  type AdcmMappingComponent,
  type AdcmMappingComponentService,
  type ComponentId,
  type HostId,
  type ServiceId,
} from '@models/adcm';
import type {
  ComponentAvailabilityErrors,
  ComponentMapping,
  ComponentsMappingObject,
  HostMapping,
  HostsDictionary,
  InitiallyMappedComponentsDictionary,
  InitiallyMappedHostsDictionary,
  ServiceMapping,
} from './ClusterMapping.types';
import type { SortParams } from '@models/table.ts';
import { HOST_MM, SERVICE_NOT_CREATED } from '@utils/mapping/componentHostRelations';
import { componentsMappingSortByName } from '@utils/mapping/mappingLayout';

export {
  validate,
  validateConstraints,
  validateDependencies,
  validateDependency,
} from '@utils/mapping/mappingValidate';
export { componentsMappingSortByName } from '@utils/mapping/mappingLayout';

export const getComponentsMapping = (
  mapping: AdcmMapping[],
  components: AdcmMappingComponent[],
  hostsDictionary: HostsDictionary,
): ComponentsMappingObject => {
  const componentsMapping: ComponentMapping[] = [];
  const unmappedHostsId: number[] = [];
  const componentHostsDictionary: Record<ComponentId, AdcmHostShortView[]> = {};

  for (const m of mapping) {
    componentHostsDictionary[m.componentId] = componentHostsDictionary[m.componentId] ?? [];

    const host = hostsDictionary[m.hostId];

    if (host) {
      componentHostsDictionary[m.componentId].push(host);
    } else {
      unmappedHostsId.push(m.hostId);
    }
  }

  for (const component of components) {
    componentsMapping.push({
      component,
      hosts: componentHostsDictionary[component.id] ?? [],
    });
  }

  return { componentsMapping, unmappedHostsId };
};

export const getHostsMapping = (
  mapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  componentsDictionary: Record<ComponentId, AdcmMappingComponent>,
  sortParams?: SortParams,
): HostMapping[] => {
  const hostComponentsDictionary: Record<HostId, AdcmMappingComponent[]> = {};

  for (const m of mapping) {
    hostComponentsDictionary[m.hostId] = hostComponentsDictionary[m.hostId] ?? [];

    const component = componentsDictionary[m.componentId];
    hostComponentsDictionary[m.hostId].push(component);
  }

  const result = hosts.map((host) => ({
    host,
    components: hostComponentsDictionary[host.id] ?? [],
  }));

  if (sortParams?.sortBy === 'name') {
    result.forEach(({ components }) => {
      components.sort((a, b) => {
        return componentsMappingSortByName(a, b);
      });
      if (sortParams.sortDirection === 'desc') {
        components.reverse();
      }
    });

    result.sort((a, b) => {
      return a.host.name.localeCompare(b.host.name);
    });
  }

  if (sortParams?.sortDirection === 'desc') {
    result.reverse();
  }

  return result;
};

export const getServicesMapping = (componentMapping: ComponentMapping[], sortParams?: SortParams): ServiceMapping[] => {
  const servicesDictionary: Record<ServiceId, AdcmMappingComponentService> = {};
  const serviceComponentsDictionary: Record<ServiceId, ComponentMapping[]> = {};

  // group components by service id
  for (const cm of componentMapping) {
    const service = cm.component.service;
    servicesDictionary[service.id] = service;
    serviceComponentsDictionary[service.id] = serviceComponentsDictionary[service.id] ?? [];
    serviceComponentsDictionary[service.id].push(cm);
  }

  const result: ServiceMapping[] = [];
  for (const [, service] of Object.entries(servicesDictionary)) {
    result.push({
      service,
      componentsMapping: serviceComponentsDictionary[service.id],
    });
  }

  if (sortParams?.sortBy === 'name') {
    result.forEach(({ componentsMapping }) => {
      componentsMapping.sort((a, b) => {
        return componentsMappingSortByName(a.component, b.component);
      });
      if (sortParams.sortDirection === 'desc') {
        componentsMapping.reverse();
      }
    });

    result.sort((a, b) => {
      return a.service.displayName.localeCompare(b.service.displayName);
    });
  }

  if (sortParams?.sortDirection === 'desc') {
    result.reverse();
  }

  return result;
};

export const mapHostsToComponent = (
  currentMapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  component: AdcmMappingComponent,
) => {
  // copy unchanged mappings
  const result: AdcmMapping[] = currentMapping.filter((mapping) => mapping.componentId !== component.id);

  // add changed mappings
  for (const host of hosts) {
    result.push({ hostId: host.id, componentId: component.id });
  }

  return result;
};

export const mapComponentsToHost = (
  currentMapping: AdcmMapping[],
  components: AdcmMappingComponent[],
  host: AdcmHostShortView,
) => {
  // copy unchanged mappings
  const result: AdcmMapping[] = currentMapping.filter((mapping) => mapping.hostId !== host.id);

  // add changed mappings
  for (const component of components) {
    result.push({ hostId: host.id, componentId: component.id });
  }

  return result;
};

export const getConstraintsLimit = (constraints: AdcmComponentConstraint[]) => {
  const [c1, c2] = constraints;
  const limit = typeof c2 === 'number' ? c2 : c1 === 'odd' ? 1 : c1;
  return limit;
};

export const checkComponentMappingAvailability = (component: AdcmMappingComponent): ComponentAvailabilityErrors => {
  const isAvailable = component.service.state === AdcmEntitySystemState.Created;

  const result: ComponentAvailabilityErrors = {
    componentNotAvailableError: !isAvailable ? SERVICE_NOT_CREATED : undefined,
  };

  return result;
};

export const checkHostMappingAvailability = (
  host: AdcmHostShortView,
  initiallyMappedHosts: Set<HostId> = new Set(),
): string | undefined => {
  // always allow revert removable INCLUDES to initial hosts
  if (initiallyMappedHosts.has(host.id)) return undefined;

  const isAvailable = host.maintenanceMode === AdcmMaintenanceMode.Off;
  return !isAvailable ? HOST_MM : undefined;
};

export const checkHostUnmappingAvailability = (
  _host: AdcmHostShortView,
  _initiallyMappedHosts: Set<HostId> = new Set(),
): string | undefined => {
  // always allow revert removable INCLUDES to initial hosts
  // if (initiallyMappedHosts.has(host.id)) return undefined;

  // now we can unmap host without constraints
  return undefined;
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

export const getInitiallyMappedComponentsDictionary = (mapping: AdcmMapping[]) => {
  const result: InitiallyMappedComponentsDictionary = {};

  for (const m of mapping) {
    if (result[m.hostId] === undefined) {
      result[m.hostId] = new Set();
    }

    result[m.hostId].add(m.componentId);
  }

  return result;
};
