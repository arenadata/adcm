import {
  type AdcmComponentConstraint,
  type AdcmComponentDependency,
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
  ComponentDependenciesMappingErrors,
  ComponentDependencyMappingErrors,
  ComponentDependencyValidationResultCacheItem,
  ComponentMapping,
  ComponentMappingErrors,
  ComponentMappingValidationResultCacheItem,
  ComponentsMappingErrors,
  ComponentsMappingObject,
  ConstraintError,
  HostMapping,
  HostsDictionary,
  InitiallyMappedComponentsDictionary,
  InitiallyMappedHostsDictionary,
  NotAddedError,
  RequiredError,
  ServiceMapping,
  ValidateRelatedData,
  ValidationCache,
} from './ClusterMapping.types';
import type { SortParams } from '@models/table.ts';

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

export const validate = (
  componentMapping: ComponentMapping[],
  relatedData: ValidateRelatedData,
): ComponentsMappingErrors => {
  const result: ComponentsMappingErrors = {};

  const validationCache: ValidationCache = {
    components: new Map(),
    dependencies: new Map(),
  };

  for (const cm of componentMapping) {
    const componentMappingErrors = validateComponent(cm, relatedData, validationCache);

    if (componentMappingErrors) {
      result[cm.component.id] = componentMappingErrors;
    }
  }

  return result;
};

const validateComponent = (
  componentMapping: ComponentMapping,
  relatedData: ValidateRelatedData,
  validationCache: ValidationCache,
): ComponentMappingErrors | undefined => {
  const { components: cache } = validationCache;

  const resultFromCache = cache.get(componentMapping.component.id);
  if (resultFromCache) {
    return resultFromCache.isValid ? undefined : resultFromCache.errors;
  }

  const constraintsError = validateConstraints(
    componentMapping.component.constraints,
    relatedData.allHostsCount,
    componentMapping.hosts.length,
  );

  const dependenciesErrors = isMandatoryComponent(componentMapping)
    ? validateDependencies(componentMapping.component, relatedData, validationCache)
    : undefined;

  let result = undefined;

  if (constraintsError || dependenciesErrors) {
    result = {
      constraintsError,
      dependenciesErrors,
    };
  }

  const cacheItem: ComponentMappingValidationResultCacheItem =
    result === undefined ? { isValid: true } : { isValid: false, errors: result };

  cache.set(componentMapping.component.id, cacheItem);

  return result;
};

export const validateConstraints = (
  constraints: AdcmComponentConstraint[],
  hostsCount: number,
  componentHostsCount: number,
): ConstraintError | undefined => {
  const [c1, c2] = constraints;
  if (constraints.length === 2 && typeof c1 === 'number' && typeof c2 === 'number') {
    return c1 <= componentHostsCount && componentHostsCount <= c2
      ? undefined
      : { type: 'constraint', message: `From ${c1} to ${c2} components should be mapped.` };
  }

  if (constraints.length === 2 && typeof c1 === 'number' && typeof c2 === 'string') {
    switch (c2) {
      case 'odd':
        return ((c1 === 0 && componentHostsCount === 0) || componentHostsCount % 2) && componentHostsCount >= c1
          ? undefined
          : {
              type: 'constraint',
              message: `${c1} or more components should be mapped. Total amount should be odd.`,
            };
      default:
        return componentHostsCount >= c1
          ? undefined
          : { type: 'constraint', message: `${c1} or more components should be mapped.` };
    }
  }

  if (constraints.length === 1 && typeof c1 === 'number') {
    return componentHostsCount === c1
      ? undefined
      : { type: 'constraint', message: `Exactly ${c1} component should be mapped.` };
  }

  if (constraints.length === 1 && typeof c1 === 'string') {
    switch (c1) {
      case '+':
        return componentHostsCount === hostsCount
          ? undefined
          : { type: 'constraint', message: 'Component should be mapped on all hosts of cluster.' };
      case 'odd':
        return componentHostsCount % 2
          ? undefined
          : { type: 'constraint', message: '1 or more components should be mapped. Total amount should be odd.' };
    }
  }

  return { type: 'constraint', message: 'Unknown constraints.' };
};

export const getConstraintsLimit = (constraints: AdcmComponentConstraint[]) => {
  const [c1, c2] = constraints;
  const limit = typeof c2 === 'number' ? c2 : c1 === 'odd' ? 1 : c1;
  return limit;
};

export const validateDependencies = (
  component: AdcmMappingComponent,
  relatedData: ValidateRelatedData,
  validationCache: ValidationCache,
): ComponentDependenciesMappingErrors | undefined => {
  if (!component.dependOn || component.dependOn.length === 0) {
    return undefined;
  }

  const notAddedErrors: NotAddedError[] = [];
  const requiredErrors: RequiredError[] = [];

  for (const { servicePrototype: dependService } of component.dependOn) {
    const dependencyErrors = validateDependency(dependService, relatedData, validationCache);
    if (dependencyErrors) {
      if (dependencyErrors.notAddedError) {
        notAddedErrors.push(dependencyErrors.notAddedError);
      }

      if (dependencyErrors.requiredError) {
        requiredErrors.push(dependencyErrors.requiredError);
      }
    }
  }

  if (requiredErrors.length === 0 && notAddedErrors.length === 0) {
    return undefined;
  }

  return {
    notAddedErrors: notAddedErrors.length ? notAddedErrors : undefined,
    requiredErrors: requiredErrors.length ? requiredErrors : undefined,
  };
};

export const validateDependency = (
  componentDependency: AdcmComponentDependency,
  relatedData: ValidateRelatedData,
  validationCache: ValidationCache,
): ComponentDependencyMappingErrors | undefined => {
  const { dependencies: cache } = validationCache;

  const resultFromCache = cache.get(componentDependency.id);
  if (resultFromCache) {
    if (resultFromCache.isValid) {
      return undefined;
    } else {
      return resultFromCache.errors;
    }
  }

  const notAddedError = validateNotAddedDependency(componentDependency, relatedData);
  const requiredError = validateRequireDependency(componentDependency, relatedData, validationCache);

  const result = notAddedError || requiredError ? { notAddedError, requiredError } : undefined;

  const cacheItem: ComponentDependencyValidationResultCacheItem = result
    ? { isValid: false, errors: result }
    : { isValid: true };

  cache.set(componentDependency.id, cacheItem);

  return result;
};

const validateNotAddedDependency = (
  servicePrototype: AdcmComponentDependency,
  relatedData: ValidateRelatedData,
): NotAddedError | undefined => {
  let result: NotAddedError | undefined = undefined;

  // component depend on not added service
  if (relatedData.notAddedServicesDictionary[servicePrototype.id]) {
    result = {
      type: 'not-added',
      params: {
        service: servicePrototype,
      },
    };
  }

  return result;
};

const validateRequireDependency = (
  servicePrototype: AdcmComponentDependency,
  relatedData: ValidateRelatedData,
  validationCache: ValidationCache,
): RequiredError | undefined => {
  const dependServiceMapping = relatedData.servicesMappingDictionary[servicePrototype.id];
  // component depend on added service (but this service have no child components)
  if (!dependServiceMapping || dependServiceMapping.componentsMapping.length === 0) {
    return undefined;
  }

  const componentPrototypesIds = new Set(servicePrototype.componentPrototypes.map(({ id }) => id));

  const requiredComponents = dependServiceMapping.componentsMapping.filter(({ component }) =>
    componentPrototypesIds.has(component.prototype.id),
  );

  for (const requiredComponentItem of requiredComponents) {
    const componentMappingErrors = validateComponent(requiredComponentItem, relatedData, validationCache);

    const isRequiredComponentsMapped = requiredComponentItem.hosts.length > 0;

    if (componentMappingErrors || !isRequiredComponentsMapped) {
      const error: RequiredError = {
        type: 'required',
        params: {
          service: servicePrototype.displayName,
          components: servicePrototype.componentPrototypes.map(({ displayName }) => displayName),
        },
      };

      return error;
    }
  }

  return undefined;
};

const isMandatoryComponent = (componentMapping: ComponentMapping) => {
  const { component, hosts } = componentMapping;

  // not mandatory when constraint [0, *] and not mapped hosts
  return !(component.constraints[0] === 0 && hosts.length === 0);
};

export const checkComponentMappingAvailability = (component: AdcmMappingComponent): ComponentAvailabilityErrors => {
  const isAvailable = component.service.state === AdcmEntitySystemState.Created;

  const result: ComponentAvailabilityErrors = {
    componentNotAvailableError: !isAvailable
      ? 'Service of this component must have "Created" state. Maintenance mode on the components must be Off'
      : undefined,
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
  return !isAvailable ? 'Maintenance mode on the host must be Off' : undefined;
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

export const componentsMappingSortByName = (a: AdcmMappingComponent, b: AdcmMappingComponent) =>
  a.displayName.localeCompare(b.displayName);

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
