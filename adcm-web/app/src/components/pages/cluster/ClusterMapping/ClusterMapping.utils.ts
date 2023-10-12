import {
  AdcmComponentConstraint,
  AdcmHostShortView,
  AdcmComponent,
  AdcmMapping,
  AdcmComponentService,
} from '@models/adcm';
import {
  HostMapping,
  ServiceMapping,
  ComponentMapping,
  ValidationResult,
  ComponentId,
  ServiceId,
  ComponentMappingValidation,
  HostId,
  HostsDictionary,
  MappingValidation,
} from './ClusterMapping.types';

export const getComponentsMapping = (
  mapping: AdcmMapping[],
  components: AdcmComponent[],
  hostsDictionary: HostsDictionary,
): ComponentMapping[] => {
  const result: ComponentMapping[] = [];
  const componentHostsDictionary: Record<ComponentId, AdcmHostShortView[]> = {};

  for (const m of mapping) {
    componentHostsDictionary[m.componentId] = componentHostsDictionary[m.componentId] ?? [];

    const host = hostsDictionary[m.hostId];
    componentHostsDictionary[m.componentId].push(host);
  }

  for (const component of components) {
    result.push({
      component,
      hosts: componentHostsDictionary[component.id] ?? [],
    });
  }

  return result;
};

export const getHostsMapping = (
  mapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  componentsDictionary: Record<ComponentId, AdcmComponent>,
): HostMapping[] => {
  const hostComponentsDictionary: Record<HostId, AdcmComponent[]> = {}; // key - component Id

  for (const m of mapping) {
    hostComponentsDictionary[m.hostId] = hostComponentsDictionary[m.hostId] ?? [];

    const component = componentsDictionary[m.componentId];
    hostComponentsDictionary[m.hostId].push(component);
  }

  const result = hosts.map((host) => ({
    host,
    components: hostComponentsDictionary[host.id] ?? [],
  }));

  return result;
};

export const getServicesMapping = (componentMapping: ComponentMapping[]): ServiceMapping[] => {
  const servicesDictionary: Record<ServiceId, AdcmComponentService> = {}; // key - service Id
  const serviceComponentsDictionary: Record<ServiceId, ComponentMapping[]> = {}; // // key - service Id

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

  return result;
};

export const validate = (componentMapping: ComponentMapping[], allHostsCount: number): MappingValidation => {
  const byComponents: Record<ComponentId, ComponentMappingValidation> = {};
  let isAllMappingValid = true;

  for (const cm of componentMapping) {
    const constraintsValidationResult = validateConstraints(cm.component.constraints, allHostsCount, cm.hosts.length);
    const requireValidationResults = validateRequire();
    const isValid = constraintsValidationResult.isValid && requireValidationResults.isValid;

    isAllMappingValid = isAllMappingValid && isValid;

    byComponents[cm.component.id] = {
      constraintsValidationResult,
      requireValidationResults,
      isValid,
    };
  }

  return {
    isAllMappingValid,
    byComponents,
  };
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
      : { isValid: false, error: `From ${c1} to ${c2} components should be installed.` };
  }

  if (constraints.length == 2 && typeof c1 === 'number' && typeof c2 === 'string') {
    switch (c2) {
      case 'odd':
        return ((c1 === 0 && componentHostsCount === 0) || componentHostsCount % 2) && componentHostsCount >= c1
          ? { isValid: true }
          : { isValid: false, error: `${c1} or more components should be installed. Total amount should be odd.` };
      case '+':
      default:
        return componentHostsCount >= c1
          ? { isValid: true }
          : { isValid: false, error: `${c1} or more components should be installed.` };
    }
  }

  if (constraints.length == 1 && typeof c1 === 'number') {
    return componentHostsCount === c1
      ? { isValid: true }
      : { isValid: false, error: `Exactly ${c1} component should be installed.` };
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
          : { isValid: false, error: '1 or more components should be installed. Total amount should be odd.' };
    }
  }

  return { isValid: false, error: 'Unknown constraints.' };
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
