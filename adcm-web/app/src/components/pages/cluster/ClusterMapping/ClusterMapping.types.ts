import type { AdcmHostShortView, AdcmMappingComponent, HostId, ComponentId } from '@models/adcm';
import type { ComponentMapping } from '@utils/mapping/mapping.types';

export type {
  HostMapping,
  ComponentMapping,
  ServiceMapping,
  RequiredError,
  NotAddedError,
  ConstraintError,
  ComponentMappingErrors,
  ComponentDependenciesMappingErrors,
  ComponentDependencyMappingErrors,
  ComponentsMappingErrors,
  ServicesDictionary,
  ComponentMappingValidationResultCacheItem,
  ComponentDependencyValidationResultCacheItem,
  ValidationCache,
  ValidateRelatedData,
} from '@utils/mapping/mapping.types';

export type HostsDictionary = Record<HostId, AdcmHostShortView>;
export type ComponentsDictionary = Record<ComponentId, AdcmMappingComponent>;

export type InitiallyMappedHostsDictionary = Record<ComponentId, Set<HostId>>;
export type InitiallyMappedComponentsDictionary = Record<HostId, Set<ComponentId>>;

export type MappingFilter = {
  hostName: string;
  componentDisplayName: string;
  isHideEmpty: boolean;
};

export type ComponentAvailabilityErrors = {
  componentNotAvailableError?: string;
  addingHostsNotAllowedError?: string;
  removingHostsNotAllowedError?: string;
};

export type ComponentsMappingObject = {
  componentsMapping: ComponentMapping[];
  unmappedHostsId: number[];
};
