import type { AdcmConfigGroup } from '@models/adcm';

export type ConfigGroupOwner = 'cluster' | 'service' | 'component' | 'hostprovider';

export type ClusterConfigGroupArgs = {
  clusterId: number;
};

export type ServiceConfigGroupArgs = {
  clusterId: number;
  serviceId: number;
};

export type ComponentConfigGroupArgs = {
  clusterId: number;
  serviceId: number;
  componentId: number;
};

export type HostProviderConfigGroupArgs = {
  hostProviderId: number;
};

export type ConfigGroupEntityArgs =
  | ClusterConfigGroupArgs
  | ServiceConfigGroupArgs
  | ComponentConfigGroupArgs
  | HostProviderConfigGroupArgs;

/** Edit-description dialog for a config group; when closed, all fields are null. */
export interface EntityDescriptionDialogState {
  configGroup: AdcmConfigGroup | null;
  entityType: ConfigGroupOwner | null;
  entityArgs: ConfigGroupEntityArgs | null;
}
