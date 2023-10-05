import { AdcmHostShortView, AdcmComponent, AdcmComponentService } from '@models/adcm';

export type ValidationError = { isValid: false; error: string };
export type ValidationSuccess = { isValid: true };
export type ValidationResult = ValidationError | ValidationSuccess;

export type HostId = AdcmHostShortView['id'];
export type ComponentId = AdcmComponent['id'];
export type ServiceId = AdcmComponentService['id'];

export type HostsDictionary = Record<HostId, AdcmHostShortView>;
export type ComponentHostsDictionary = Record<ComponentId, AdcmHostShortView[]>;
export type ComponentsDictionary = Record<ComponentId, AdcmComponent>;

export type HostMappingFilter = {
  componentDisplayName: string;
  isHideEmptyHosts: boolean;
};

export type HostMapping = {
  host: AdcmHostShortView;
  components: AdcmComponent[];
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
  service: AdcmComponentService;
  componentsMapping: ComponentMapping[];
};

export type ComponentMapping = {
  component: AdcmComponent;
  hosts: AdcmHostShortView[];
};

export type MappingState = 'no-changes' | 'editing' | 'saved';
