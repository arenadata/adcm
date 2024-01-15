import { AdcmConfig, SchemaDefinition } from '@models/adcm';

export type EntityType =
  | 'settings'
  | 'host-provider'
  | 'host-provider-config-group'
  | 'cluster'
  | 'cluster-config-group'
  | 'host'
  | 'service'
  | 'service-config-group'
  | 'service-component'
  | 'service-component-config-group';

// eslint-disable-next-line @typescript-eslint/no-empty-interface
export interface LoadConfigurationArgs {}

/* Settings */

export interface LoadSettingsConfigurationArgs extends LoadConfigurationArgs {
  configId: number;
}

/* Host provider */

export interface LoadHostProviderConfigurationArgs extends LoadConfigurationArgs {
  hostProviderId: number;
  configId: number;
}

export interface LoadHostProviderGroupConfigurationArgs extends LoadConfigurationArgs {
  hostProviderId: number;
  configGroupId: number;
  configId: number;
}

/* Cluster */

export interface LoadClusterConfigurationArgs extends LoadConfigurationArgs {
  clusterId: number;
  configId: number;
}

export type LoadClusterGroupConfigurationArgs = {
  clusterId: number;
  configGroupId: number;
  configId: number;
};

/* Host */

export type LoadHostConfigurationArgs = {
  hostId: number;
  configId: number;
};

/* Service */

export type LoadServiceConfigurationArgs = {
  clusterId: number;
  serviceId: number;
  configId: number;
};

export type LoadServiceGroupConfigurationArgs = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
  configId: number;
};

/* Service component */

export type LoadServiceComponentConfigurationArgs = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configId: number;
};

export type LoadServiceComponentGroupConfigurationArgs = {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
  configId: number;
};

export type LoadEntityConfigurationArgs =
  | {
      entityType: 'settings';
      args: LoadSettingsConfigurationArgs;
    }
  | {
      entityType: 'host-provider';
      args: LoadHostProviderConfigurationArgs;
    }
  | {
      entityType: 'host-provider-config-group';
      args: LoadHostProviderGroupConfigurationArgs;
    }
  | {
      entityType: 'cluster';
      args: LoadClusterConfigurationArgs;
    }
  | {
      entityType: 'cluster-config-group';
      args: LoadClusterGroupConfigurationArgs;
    }
  | {
      entityType: 'host';
      args: LoadHostConfigurationArgs;
    }
  | {
      entityType: 'service';
      args: LoadServiceConfigurationArgs;
    }
  | {
      entityType: 'service-config-group';
      args: LoadServiceGroupConfigurationArgs;
    }
  | {
      entityType: 'service-component';
      args: LoadServiceComponentConfigurationArgs;
    }
  | {
      entityType: 'service-component-config-group';
      args: LoadServiceComponentGroupConfigurationArgs;
    };

export type ApiRequestsDictionary = {
  [key in EntityType]: {
    getConfig: (args: LoadConfigurationArgs) => Promise<AdcmConfig>;
    getConfigSchema: (args: LoadConfigurationArgs) => Promise<SchemaDefinition>;
  };
};
