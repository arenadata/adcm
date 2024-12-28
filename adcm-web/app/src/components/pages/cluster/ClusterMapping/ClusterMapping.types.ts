import type {
  AdcmHostShortView,
  AdcmMappingComponent,
  AdcmMappingComponentService,
  AdcmServicePrototype,
  HostId,
  ComponentId,
  ServiceId,
  ServicePrototypeId,
  AdcmComponentDependency,
} from '@models/adcm';

export type RequiredError = {
  type: 'required';
  params: {
    service: string;
    components: string[];
  };
};

export type NotAddedError = {
  type: 'not-added';
  params: {
    service: AdcmComponentDependency;
  };
};

export type ConstraintError = {
  type: 'constraint';
  message: string;
};

export type ComponentMappingErrors = {
  constraintsError?: ConstraintError;
  dependenciesErrors?: ComponentDependenciesMappingErrors;
};

export type ComponentDependenciesMappingErrors = {
  notAddedErrors?: NotAddedError[];
  requiredErrors?: RequiredError[];
};

export type ComponentDependencyMappingErrors = {
  notAddedError?: NotAddedError;
  requiredError?: RequiredError;
};

export type HostsDictionary = Record<HostId, AdcmHostShortView>;
export type ComponentHostsDictionary = Record<ComponentId, AdcmHostShortView[]>;
export type ComponentsDictionary = Record<ComponentId, AdcmMappingComponent>;
export type ServicesDictionary = Record<ServiceId, AdcmServicePrototype>;

export type InitiallyMappedHostsDictionary = Record<ComponentId, Set<HostId>>;

export type ComponentsMappingErrors = Record<ComponentId, ComponentMappingErrors>;

export type HostMapping = {
  host: AdcmHostShortView;
  components: AdcmMappingComponent[];
};

export type MappingFilter = {
  hostName: string;
  componentDisplayName: string;
  isHideEmpty: boolean;
};

export type ServiceMapping = {
  service: AdcmMappingComponentService;
  componentsMapping: ComponentMapping[];
};

export type ComponentMapping = {
  component: AdcmMappingComponent;
  hosts: AdcmHostShortView[];
};

type ValidationSuccess = { isValid: true };
type ValidationFailed<T> = { isValid: false; errors: T };
type ValidationResultCacheItem<T> = ValidationSuccess | ValidationFailed<T>;
export type ComponentMappingValidationResultCacheItem = ValidationResultCacheItem<ComponentMappingErrors>;
export type ComponentDependencyValidationResultCacheItem = ValidationResultCacheItem<ComponentDependencyMappingErrors>;

export type ValidationCache = {
  components: Map<ComponentId, ComponentMappingValidationResultCacheItem>;
  dependencies: Map<ServicePrototypeId, ComponentDependencyValidationResultCacheItem>;
};

export type ValidateRelatedData = {
  servicesMappingDictionary: Record<ServicePrototypeId, ServiceMapping>;
  notAddedServicesDictionary: ServicesDictionary;
  allHostsCount: number;
};

export type ComponentAvailabilityErrors = {
  componentNotAvailableError?: string;
  addingHostsNotAllowedError?: string;
  removingHostsNotAllowedError?: string;
};
