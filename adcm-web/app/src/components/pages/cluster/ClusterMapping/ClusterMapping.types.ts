import { AdcmHostShortView, AdcmComponent, AdcmComponentService } from '@models/adcm';

export type ValidationResult = { isValid: false; error: string } | { isValid: true };
export type ValidationSummary = 'valid' | 'error' | 'warning';

export type HostMappingFilter = {
  componentDisplayName: string;
};

export type HostMapping = {
  host: AdcmHostShortView;
  components: AdcmComponent[];
};

export type ComponentMapping = {
  component: AdcmComponent;
  hosts: AdcmHostShortView[];
  filteredHosts: AdcmHostShortView[];
  constraintsValidationResult: ValidationResult;
  requireValidationResults: ValidationResult;
  validationSummary: ValidationSummary;
};

export type ServiceMappingFilter = {
  hostName: string;
};

export type ServiceMapping = {
  service: AdcmComponentService;
  componentsMapping: ComponentMapping[];
  validationSummary: ValidationSummary;
};
