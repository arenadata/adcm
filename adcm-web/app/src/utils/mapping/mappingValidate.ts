import type { AdcmComponentConstraint, AdcmComponentDependency, AdcmMappingComponent } from '@models/adcm';
import type {
  ComponentDependenciesMappingErrors,
  ComponentDependencyMappingErrors,
  ComponentDependencyValidationResultCacheItem,
  ComponentMapping,
  ComponentMappingErrors,
  ComponentMappingValidationResultCacheItem,
  ComponentsMappingErrors,
  ConstraintError,
  NotAddedError,
  RequiredError,
  ValidateRelatedData,
  ValidationCache,
} from './mapping.types';

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

  return !(component.constraints[0] === 0 && hosts.length === 0);
};
