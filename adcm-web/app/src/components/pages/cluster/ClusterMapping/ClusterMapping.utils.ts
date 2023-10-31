import {
  AdcmComponentConstraint,
  AdcmHostShortView,
  AdcmMappingComponent,
  AdcmMapping,
  AdcmMappingComponentService,
  AdcmDependOnService,
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
  ValidateCache,
  ComponentValidateResult,
  ValidateRelatedData,
  ValidationSuccess,
} from './ClusterMapping.types';

export const getComponentsMapping = (
  mapping: AdcmMapping[],
  components: AdcmMappingComponent[],
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
  componentsDictionary: Record<ComponentId, AdcmMappingComponent>,
): HostMapping[] => {
  const hostComponentsDictionary: Record<HostId, AdcmMappingComponent[]> = {}; // key - component Id

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
  const servicesDictionary: Record<ServiceId, AdcmMappingComponentService> = {}; // key - serviceId
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

export const validate = (componentMapping: ComponentMapping[], relatedData: ValidateRelatedData): MappingValidation => {
  const byComponents: Record<ComponentId, ComponentMappingValidation> = {};
  let isAllMappingValid = true;
  const validateCash: ValidateCache = {
    componentsCache: new Map(),
    servicesCache: new Map(),
  };

  for (const cm of componentMapping) {
    const { constraintsValidationResult, requireValidationResults } = validateComponent(cm, relatedData, validateCash);

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
  component: AdcmMappingComponent,
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
      : { isValid: false, errors: [`From ${c1} to ${c2} components should be installed.`] };
  }

  if (constraints.length == 2 && typeof c1 === 'number' && typeof c2 === 'string') {
    switch (c2) {
      case 'odd':
        return ((c1 === 0 && componentHostsCount === 0) || componentHostsCount % 2) && componentHostsCount >= c1
          ? { isValid: true }
          : { isValid: false, errors: [`${c1} or more components should be installed. Total amount should be odd.`] };
      case '+':
      default:
        return componentHostsCount >= c1
          ? { isValid: true }
          : { isValid: false, errors: [`${c1} or more components should be installed.`] };
    }
  }

  if (constraints.length == 1 && typeof c1 === 'number') {
    return componentHostsCount === c1
      ? { isValid: true }
      : { isValid: false, errors: [`Exactly ${c1} component should be installed.`] };
  }

  if (constraints.length == 1 && typeof c1 === 'string') {
    switch (c1) {
      case '+':
        return componentHostsCount === hostsCount
          ? { isValid: true }
          : { isValid: false, errors: ['Component should be installed on all hosts of cluster.'] };
      case 'odd':
        return componentHostsCount % 2
          ? { isValid: true }
          : { isValid: false, errors: ['1 or more components should be installed. Total amount should be odd.'] };
    }
  }

  return { isValid: false, errors: ['Unknown constraints.'] };
};

export const getConstraintsLimit = (constraints: AdcmComponentConstraint[]) => {
  const [c1, c2] = constraints;
  const limit = typeof c2 === 'number' ? c2 : c1 === 'odd' ? 1 : c1;
  return limit;
};

export const validateDependOn = (
  component: AdcmMappingComponent,
  relatedData: ValidateRelatedData,
  validateCash: ValidateCache,
): ValidationResult => {
  // component have not dependencies
  if (!component.dependOn || component.dependOn.length === 0) {
    return { isValid: true };
  }

  const errors = [];
  for (const { servicePrototype: dependService } of component.dependOn) {
    // component depend on not added service
    if (!validateServiceRequire(dependService, relatedData, validateCash)) {
      let error = `Requires mapping of service "${dependService.displayName}"`;

      // when component depend on special components of service
      if (dependService.componentPrototypes.length > 0) {
        const componentsNames = dependService.componentPrototypes.map(({ displayName }) => displayName);
        error += ` (components: ${componentsNames.join(', ')})`;
      }
      errors.push(error);
    }
  }

  if (errors.length > 0) {
    return {
      isValid: false,
      errors,
    };
  }

  return { isValid: true };
};

const validateServiceRequire = (
  servicePrototype: AdcmDependOnService['servicePrototype'],
  relatedData: ValidateRelatedData,
  validateCash: ValidateCache,
) => {
  const { servicesCache } = validateCash;
  if (servicesCache.has(servicePrototype.id)) {
    return servicesCache.get(servicePrototype.id);
  }

  const { notAddedServicesDictionary, servicesMappingDictionary } = relatedData;

  // component depend on not added service
  if (notAddedServicesDictionary[servicePrototype.id]) {
    servicesCache.set(servicePrototype.id, false);
    return false;
  }

  const dependServiceMapping = servicesMappingDictionary[servicePrototype.id];
  // component depend on added service (but this service have no child components)
  if (!dependServiceMapping || dependServiceMapping.componentsMapping.length === 0) {
    servicesCache.set(servicePrototype.id, true);
    return true;
  }

  const componentPrototypesIds = servicePrototype.componentPrototypes.map(({ id }) => id);

  const requiredComponents = dependServiceMapping.componentsMapping.filter(({ component }) =>
    componentPrototypesIds.includes(component.prototype.id),
  );

  for (const requiredComponentItem of requiredComponents) {
    const { constraintsValidationResult, requireValidationResults } = validateComponent(
      requiredComponentItem,
      relatedData,
      validateCash,
    );
    const isValidChildComponent = constraintsValidationResult.isValid && requireValidationResults.isValid;

    const isMappedChildComponent = requiredComponentItem.hosts.length > 0;

    if (!isValidChildComponent || !isMappedChildComponent) {
      servicesCache.set(servicePrototype.id, false);
      return false;
    }
  }

  servicesCache.set(servicePrototype.id, true);
  return true;
};

const validateComponent = (
  componentMapping: ComponentMapping,
  relatedData: ValidateRelatedData,
  validateCash: ValidateCache,
) => {
  const { componentsCache } = validateCash;
  if (componentsCache.has(componentMapping.component.id)) {
    return componentsCache.get(componentMapping.component.id) as ComponentValidateResult;
  }

  const constraintsValidationResult = validateConstraints(
    componentMapping.component.constraints,
    relatedData.allHostsCount,
    componentMapping.hosts.length,
  );

  // if component can be not mapping (constraint = [0,...]) and user not mapped some hosts to this component
  // then we can ignore validateDependOn for this component
  const requireValidationResults = isMandatoryComponent(componentMapping)
    ? validateDependOn(componentMapping.component, relatedData, validateCash)
    : ({ isValid: true } as ValidationSuccess);

  const result = {
    constraintsValidationResult,
    requireValidationResults,
  };

  componentsCache.set(componentMapping.component.id, result);

  return result;
};

const isMandatoryComponent = (componentMapping: ComponentMapping) => {
  const { component, hosts } = componentMapping;

  // not mandatory when constraint [0, *] and not mapped hosts
  return !(component.constraints[0] === 0 && hosts.length === 0);
};

export const isComponentDependOnNotAddedServices = (
  component: AdcmMappingComponent,
  notAddedServicesDictionary: ValidateRelatedData['notAddedServicesDictionary'],
) => {
  if (!component.dependOn?.length) return false;

  return component.dependOn.some(({ servicePrototype }) => !!notAddedServicesDictionary[servicePrototype.id]);
};
