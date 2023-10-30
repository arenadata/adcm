import {
  AdcmHostShortView,
  AdcmMappingComponent,
  AdcmMappingComponentService,
  AdcmServicePrototype,
} from '@models/adcm';

export type ValidationError = { isValid: false; errors: string[] };
export type ValidationSuccess = { isValid: true };
export type ValidationResult = ValidationError | ValidationSuccess;

export type HostId = AdcmHostShortView['id'];
export type ComponentId = AdcmMappingComponent['id'];
export type ServiceId = AdcmMappingComponentService['id'];

export type HostsDictionary = Record<HostId, AdcmHostShortView>;
export type ComponentHostsDictionary = Record<ComponentId, AdcmHostShortView[]>;
export type ComponentsDictionary = Record<ComponentId, AdcmMappingComponent>;

export type HostMappingFilter = {
  componentDisplayName: string;
  isHideEmptyHosts: boolean;
};

export type HostMapping = {
  host: AdcmHostShortView;
  components: AdcmMappingComponent[];
};

export type MappingValidation = {
  isAllMappingValid: boolean;
  byComponents: Record<ComponentId, ComponentMappingValidation>;
};

export type ComponentMappingValidation = {
  constraintsValidationResult: ValidationResult;
  requireValidationResults: ValidationResult;
  isValid: boolean;
};

export type ServiceMappingFilter = {
  hostName: string;
  isHideEmptyComponents: boolean;
};

export type ServiceMapping = {
  service: AdcmMappingComponentService;
  componentsMapping: ComponentMapping[];
};

export type ComponentMapping = {
  component: AdcmMappingComponent;
  hosts: AdcmHostShortView[];
};

export type MappingState = 'no-changes' | 'editing' | 'saved';

export type ComponentValidateResult = {
  constraintsValidationResult: ValidationResult;
  requireValidationResults: ValidationResult;
};

export type ValidateCache = {
  componentsCache: Map<number, ComponentValidateResult>;
  servicesCache: Map<AdcmServicePrototype['id'], boolean>;
};

export type ValidateRelatedData = {
  servicesMappingDictionary: Record<AdcmServicePrototype['id'], ServiceMapping>;
  notAddedServicesDictionary: Record<ServiceId, AdcmServicePrototype>;
  allHostsCount: number;
};
