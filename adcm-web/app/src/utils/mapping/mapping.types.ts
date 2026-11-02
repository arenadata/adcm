import type {
  AdcmComponentDependency,
  AdcmHostComponentMapRuleAction,
  AdcmHostShortView,
  AdcmMappingComponent,
  AdcmMappingComponentService,
  AdcmServicePrototype,
  ComponentId,
  HostId,
  ServiceId,
  ServicePrototypeId,
} from '@models/adcm';
import type { SortDirection } from '@models/table';

export type HostMapping = {
  host: AdcmHostShortView;
  components: AdcmMappingComponent[];
};

export type ComponentMapping = {
  component: AdcmMappingComponent;
  hosts: AdcmHostShortView[];
};

export type ServiceMapping = {
  service: AdcmMappingComponentService;
  componentsMapping: ComponentMapping[];
  hasErrors?: boolean;
};

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

export type ComponentDependenciesMappingErrors = {
  notAddedErrors?: NotAddedError[];
  requiredErrors?: RequiredError[];
};

export type ComponentDependencyMappingErrors = {
  notAddedError?: NotAddedError;
  requiredError?: RequiredError;
};

export type ComponentMappingErrors = {
  constraintsError?: ConstraintError;
  dependenciesErrors?: ComponentDependenciesMappingErrors;
};

export type ComponentsMappingErrors = Record<ComponentId, ComponentMappingErrors>;

export type ServicesDictionary = Record<ServiceId, AdcmServicePrototype>;

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

export type MappingModel = {
  componentsMapping: ComponentMapping[];
  hostsMapping: HostMapping[];
  servicesMapping: ServiceMapping[];
  unmappedHostsId: number[];
};

export type MappingActionRule = {
  service: string;
  component: string;
  operation: AdcmHostComponentMapRuleAction;
};

export type MappingAvailabilityStrategy =
  | { type: 'cluster' }
  | {
      type: 'actionRules';
      rules: MappingActionRule[];
    };

export type MappingRelationsPolicy = MappingAvailabilityStrategy;

export type PairKey = `${number}_${number}`;

export type PairRelation = {
  map: { denyReasons: string[] };
  unmap: { denyReasons: string[] };
};

export type ComponentHostRelations = {
  pairs: Map<PairKey, PairRelation>;
  componentLevelDenies: Map<ComponentId, string>;
};

export type MappingItemAvailability = {
  canMap: boolean;
  canUnmap: boolean;
  notAvailableReason?: string;
};

export type MappingAvailability = {
  components: Record<ComponentId, MappingItemAvailability>;
  hosts: Record<HostId, MappingItemAvailability>;
  services: Record<number, { isEditable: boolean }>;
};

export type MappingLayoutKind = 'services' | 'flat' | 'hosts';
export type MappingSortKind = 'name' | 'editableFirst';

export type MappingViewConfig = {
  strategy: MappingAvailabilityStrategy;
  kind: MappingLayoutKind;
  sort: MappingSortKind;
  sortDirection?: SortDirection;
};

export type ComponentMappingWithAvailability = ComponentMapping & { availability: MappingItemAvailability };

export type MappingViewModel =
  | {
      kind: 'services';
      services: Array<
        ServiceMapping & {
          isEditable: boolean;
          componentsMapping: ComponentMappingWithAvailability[];
        }
      >;
    }
  | {
      kind: 'flat';
      components: ComponentMappingWithAvailability[];
    }
  | {
      kind: 'hosts';
      hosts: Array<HostMapping & { isEditable: boolean }>;
    };
