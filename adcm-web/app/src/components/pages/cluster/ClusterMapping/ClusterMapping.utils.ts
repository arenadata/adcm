import {
  AdcmComponentConstraint,
  AdcmHostShortView,
  AdcmComponent,
  AdcmMapping,
  AdcmComponentService,
} from '@models/adcm';
import {
  HostMappingFilter,
  HostMapping,
  ServiceMappingFilter,
  ServiceMapping,
  ComponentMapping,
  ValidationResult,
  ValidationSummary,
} from './ClusterMapping.types';

export const getHostsMapping = (
  hosts: AdcmHostShortView[],
  mapping: AdcmMapping[],
  componentsDictionary: Record<number, AdcmComponent>,
  filter: HostMappingFilter,
): HostMapping[] => {
  const hostComponentsDictionary: Record<number, AdcmComponent[]> = {}; // key - component Id

  for (const m of mapping) {
    hostComponentsDictionary[m.hostId] = hostComponentsDictionary[m.hostId] ?? [];

    const component = componentsDictionary[m.componentId];
    if (!component.displayName.toLowerCase().includes(filter.componentDisplayName.toLowerCase())) {
      continue;
    } else {
      hostComponentsDictionary[m.hostId].push(component);
    }
  }

  const result = hosts.map((host) => ({
    host,
    components: hostComponentsDictionary[host.id] ?? [],
  }));

  return result;
};

export const getServicesMapping = (
  components: AdcmComponent[],
  mapping: AdcmMapping[],
  hostsDictionary: Record<number, AdcmHostShortView>,
  filter: ServiceMappingFilter,
): ServiceMapping[] => {
  const componentHostsDictionary: Record<number, AdcmHostShortView[]> = {}; // key - component Id
  const filteredComponentHostsDictionary: Record<number, AdcmHostShortView[]> = {}; // key - component Id
  const allHostsCount = Object.keys(hostsDictionary).length;

  // group hosts by component id
  for (const m of mapping) {
    componentHostsDictionary[m.componentId] = componentHostsDictionary[m.componentId] ?? [];
    filteredComponentHostsDictionary[m.componentId] = filteredComponentHostsDictionary[m.componentId] ?? [];

    const host = hostsDictionary[m.hostId];
    componentHostsDictionary[m.componentId].push(host);

    if (host.name.toLowerCase().includes(filter.hostName.toLowerCase())) {
      filteredComponentHostsDictionary[m.componentId].push(host);
    }
  }

  const uniqueServiceIds: number[] = [];
  const servicesDictionary: Record<number, AdcmComponentService> = {}; // key - service Id
  const serviceComponentsDictionary: Record<number, ComponentMapping[]> = {}; // // key - service Id

  // group components by service id
  for (const c of components) {
    if (!servicesDictionary[c.service.id]) {
      servicesDictionary[c.service.id] = c.service;
      uniqueServiceIds.push(c.service.id);
    }

    const componentHosts = componentHostsDictionary[c.id] ?? [];
    const constraintsValidationResult = validateConstraints(c.constraints, allHostsCount, componentHosts.length);
    const requireValidationResults = validateRequire();
    const componentValidationSummary = getComponentValidationSummary(
      constraintsValidationResult.isValid,
      requireValidationResults.isValid,
    );

    (serviceComponentsDictionary[c.service.id] = serviceComponentsDictionary[c.service.id] ?? []).push({
      component: c,
      hosts: componentHosts,
      constraintsValidationResult,
      requireValidationResults,
      filteredHosts: filteredComponentHostsDictionary[c.id] ?? [],
      validationSummary: componentValidationSummary,
    });
  }

  const result: ServiceMapping[] = uniqueServiceIds.map((serviceId) => ({
    service: servicesDictionary[serviceId],
    componentsMapping: serviceComponentsDictionary[serviceId],
    validationSummary: getServiceValidationSummary(serviceComponentsDictionary[serviceId]),
  }));

  return result;
};

export const mapComponentsToHost = (
  hostsMapping: HostMapping[],
  components: AdcmComponent[],
  host: AdcmHostShortView,
) => {
  const result: AdcmMapping[] = [];

  // copy unchanged mappings
  for (const mapping of hostsMapping) {
    if (host.id !== mapping.host.id) {
      for (const component of mapping.components) {
        result.push({ hostId: mapping.host.id, componentId: component.id });
      }
    }
  }

  // add changed mappings
  for (const component of components) {
    result.push({ hostId: host.id, componentId: component.id });
  }

  return result;
};

export const mapHostsToComponent = (
  servicesMapping: ServiceMapping[],
  hosts: AdcmHostShortView[],
  component: AdcmComponent,
) => {
  const result: AdcmMapping[] = [];

  // copy unchanged mappings
  for (const service of servicesMapping) {
    for (const mapping of service.componentsMapping) {
      if (component.id !== mapping.component.id) {
        for (const host of mapping.hosts) {
          result.push({ hostId: host.id, componentId: mapping.component.id });
        }
      }
    }
  }

  // add changed mappings
  for (const host of hosts) {
    result.push({ hostId: host.id, componentId: component.id });
  }

  return result;
};

export const validateConstraints = (
  constraints: AdcmComponentConstraint[],
  hostsCount: number,
  componentHostsCount: number,
): ValidationResult => {
  const [c1, c2] = constraints;
  if (constraints.length == 2 && typeof c1 === 'number' && typeof c2 === 'number') {
    return c1 <= componentHostsCount && componentHostsCount <= c2
      ? { isValid: true }
      : { isValid: false, error: `Must be installed at least ${c1} and no more ${c2} components.` };
  }

  if (constraints.length == 2 && typeof c1 === 'number' && typeof c2 === 'string') {
    switch (c2) {
      case 'odd':
        return ((c1 === 0 && componentHostsCount === 0) || componentHostsCount % 2) && componentHostsCount >= c1
          ? { isValid: true }
          : { isValid: false, error: `Must be installed at least ${c1} components. Total amount should be odd.` };
      case '+':
      default:
        return componentHostsCount >= c1
          ? { isValid: true }
          : { isValid: false, error: `Must be installed at least ${c1} components.` };
    }
  }

  if (constraints.length == 1 && typeof c1 === 'number') {
    return componentHostsCount === c1
      ? { isValid: true }
      : { isValid: false, error: `Exactly ${c1} component should be installed` };
  }

  if (constraints.length == 1 && typeof c1 === 'string') {
    switch (c1) {
      case '+':
        return componentHostsCount === hostsCount
          ? { isValid: true }
          : { isValid: false, error: 'Component should be installed on all hosts of cluster.' };
      case 'odd':
        return componentHostsCount % 2
          ? { isValid: true }
          : { isValid: false, error: 'One or more component should be installed. Total amount should be odd.' };
    }
  }

  return { isValid: false, error: 'Unknown constraints' };
};

export const getConstraintsLimit = (constraints: AdcmComponentConstraint[]) => {
  const [c1, c2] = constraints;
  const limit = typeof c2 === 'number' ? c2 : c1 === 'odd' ? 1 : c1;
  return limit;
};

// TODO: implement
export const validateRequire = (): ValidationResult => {
  return { isValid: true };
};

export const getComponentValidationSummary = (
  isConstraintValid: boolean,
  isRequireValid: boolean,
): ValidationSummary => {
  if (isConstraintValid && isRequireValid) {
    return 'valid';
  }

  if (isConstraintValid && !isRequireValid) {
    return 'warning';
  }

  return 'error';
};

export const getServiceValidationSummary = (componentMapping: ComponentMapping[]): ValidationSummary => {
  let result: ValidationSummary = 'valid';

  for (const mapping of componentMapping) {
    if (mapping.validationSummary === 'error') {
      result = 'error';
      break;
    } else if (mapping.validationSummary === 'warning') {
      result = 'warning';
    }
  }

  return result;
};
