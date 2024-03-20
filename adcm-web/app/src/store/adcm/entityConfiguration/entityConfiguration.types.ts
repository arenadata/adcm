import { AdcmConfig, AdcmConfigShortView, Batch, SchemaDefinition } from '@models/adcm';

import { GetSettingsConfigArgs, CreateSettingsConfigArgs } from '@api/adcm/settings';
import { GetClusterConfigsArgs, GetClusterConfigArgs, CreateClusterConfigArgs } from '@api/adcm/clusterConfigs';
import {
  GetClusterGroupConfigsArgs,
  GetClusterGroupConfigArgs,
  CreateClusterGroupConfigArgs,
} from '@api/adcm/clusterGroupConfigConfigs';
import {
  GetHostProviderConfigsArgs,
  GetHostProviderConfigArgs,
  CreateHostProviderConfigArgs,
} from '@api/adcm/hostProviderConfigs';
import {
  GetHostProviderGroupConfigsArgs,
  GetHostProviderGroupConfigArgs,
  CreateHostProviderGroupConfigArgs,
} from '@api/adcm/hostProviderGroupConfigConfigs';
import { GetHostConfigsArgs, GetHostConfigArgs, CreateHostConfigArgs } from '@api/adcm/hostConfigs';
import {
  GetClusterServiceConfigsArgs,
  GetClusterServiceConfigArgs,
  CreateClusterServiceConfigArgs,
} from '@api/adcm/clusterServicesConfigs';
import {
  GetClusterServiceGroupConfigsArgs,
  GetClusterServiceGroupConfigArgs,
  CreateClusterServiceGroupConfigArgs,
} from '@api/adcm/clusterServiceGroupConfigConfigs';
import {
  GetClusterServiceComponentConfigsArgs,
  GetClusterServiceComponentConfigArgs,
  CreateClusterServiceComponentConfigArgs,
} from '@api/adcm/clusterServiceComponentsConfigs';
import {
  GetClusterServiceComponentGroupConfigsArgs,
  GetClusterServiceComponentGroupConfigArgs,
  CreateClusterServiceComponentGroupConfigArgs,
} from '@api/adcm/serviceComponentGroupConfigConfigs';

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

export interface LoadConfigurationVersionsArgs {}

export interface LoadConfigurationArgs {}

export interface SaveConfigurationArgs {}

/* Settings */
export interface LoadSettingsConfigurationArgs extends LoadConfigurationArgs, GetSettingsConfigArgs {}
export interface SaveSettingsConfigurationArgs extends SaveConfigurationArgs, CreateSettingsConfigArgs {}

/* Host provider */
// eslint-disable-next-line prettier/prettier
export interface LoadHostProviderConfigurationVersionsArgs extends LoadConfigurationVersionsArgs, GetHostProviderConfigsArgs {}
export interface LoadHostProviderConfigurationArgs extends LoadConfigurationArgs, GetHostProviderConfigArgs {}
export interface SaveHostProviderConfigurationArgs extends SaveConfigurationArgs, CreateHostProviderConfigArgs {}

/* Host provider group */
export interface LoadHostProviderGroupConfigurationVersionsArgs
  extends LoadConfigurationVersionsArgs,
    GetHostProviderGroupConfigsArgs {}
export interface LoadHostProviderGroupConfigurationArgs extends LoadConfigurationArgs, GetHostProviderGroupConfigArgs {}
export interface SaveHostProviderGroupConfigurationArgs
  extends SaveConfigurationArgs,
    CreateHostProviderGroupConfigArgs {}

/* Cluster */
export interface LoadClusterConfigurationVersionsArgs extends LoadConfigurationVersionsArgs, GetClusterConfigsArgs {}
export interface LoadClusterConfigurationArgs extends LoadConfigurationArgs, GetClusterConfigArgs {}
export interface SaveClusterConfigurationArgs extends SaveConfigurationArgs, CreateClusterConfigArgs {}

/* Cluster group */
export interface LoadClusterGroupConfigurationVersionsArgs
  extends LoadConfigurationVersionsArgs,
    GetClusterGroupConfigsArgs {}
export interface LoadClusterGroupConfigurationArgs extends LoadConfigurationArgs, GetClusterGroupConfigArgs {}
export interface SaveClusterGroupConfigurationArgs extends SaveConfigurationArgs, CreateClusterGroupConfigArgs {}

/* Host */
export interface LoadHostConfigurationVersionsArgs extends LoadConfigurationVersionsArgs, GetHostConfigsArgs {}
export interface LoadHostConfigurationArgs extends LoadConfigurationArgs, GetHostConfigArgs {}
export interface SaveHostConfigurationArgs extends SaveConfigurationArgs, CreateHostConfigArgs {}

/* Cluster service */
export interface LoadClusterServiceConfigurationVersionsArgs
  extends LoadConfigurationVersionsArgs,
    GetClusterServiceConfigsArgs {}
export interface LoadClusterServiceConfigurationArgs extends LoadConfigurationArgs, GetClusterServiceConfigArgs {}
export interface SaveClusterServiceConfigurationArgs extends SaveConfigurationArgs, CreateClusterServiceConfigArgs {}

/* Cluster service group */
export interface LoadClusterServiceGroupConfigurationVersionsArgs
  extends LoadConfigurationVersionsArgs,
    GetClusterServiceGroupConfigsArgs {}
export interface LoadClusterServiceGroupConfigurationArgs
  extends LoadConfigurationArgs,
    GetClusterServiceGroupConfigArgs {}
export interface SaveClusterServiceGroupConfigurationArgs
  extends SaveConfigurationArgs,
    CreateClusterServiceGroupConfigArgs {}

/* Service component */
export interface LoadClusterServiceComponentConfigurationVersionsArgs
  extends LoadConfigurationVersionsArgs,
    GetClusterServiceComponentConfigsArgs {}
export interface LoadClusterServiceComponentConfigurationArgs
  extends LoadConfigurationArgs,
    GetClusterServiceComponentConfigArgs {}
export interface SaveClusterServiceComponentConfigurationArgs
  extends SaveConfigurationArgs,
    CreateClusterServiceComponentConfigArgs {}

/* Service component group */
export interface LoadClusterServiceComponentGroupConfigurationVersionsArgs
  extends LoadConfigurationVersionsArgs,
    GetClusterServiceComponentGroupConfigsArgs {}
export interface LoadClusterServiceComponentGroupConfigurationArgs
  extends LoadConfigurationArgs,
    GetClusterServiceComponentGroupConfigArgs {}
export interface SaveClusterServiceComponentGroupConfigurationArgs
  extends SaveConfigurationArgs,
    CreateClusterServiceComponentGroupConfigArgs {}

export type LoadEntityConfigurationVersionsArgs =
  | {
      entityType: 'settings';
      args: LoadConfigurationVersionsArgs;
    }
  | {
      entityType: 'host-provider';
      args: LoadHostProviderConfigurationVersionsArgs;
    }
  | {
      entityType: 'host-provider-config-group';
      args: LoadHostProviderGroupConfigurationVersionsArgs;
    }
  | {
      entityType: 'cluster';
      args: LoadClusterConfigurationVersionsArgs;
    }
  | {
      entityType: 'cluster-config-group';
      args: LoadClusterGroupConfigurationVersionsArgs;
    }
  | {
      entityType: 'host';
      args: LoadHostConfigurationVersionsArgs;
    }
  | {
      entityType: 'service';
      args: LoadClusterServiceConfigurationVersionsArgs;
    }
  | {
      entityType: 'service-config-group';
      args: LoadClusterServiceGroupConfigurationVersionsArgs;
    }
  | {
      entityType: 'service-component';
      args: LoadClusterServiceComponentConfigurationVersionsArgs;
    }
  | {
      entityType: 'service-component-config-group';
      args: LoadClusterServiceComponentGroupConfigurationVersionsArgs;
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
      args: LoadClusterServiceConfigurationArgs;
    }
  | {
      entityType: 'service-config-group';
      args: LoadClusterServiceGroupConfigurationArgs;
    }
  | {
      entityType: 'service-component';
      args: LoadClusterServiceComponentConfigurationArgs;
    }
  | {
      entityType: 'service-component-config-group';
      args: LoadClusterServiceComponentGroupConfigurationArgs;
    };

export type CreateEntityConfigurationArgs =
  | {
      entityType: 'settings';
      args: SaveSettingsConfigurationArgs;
    }
  | {
      entityType: 'host-provider';
      args: SaveHostProviderConfigurationArgs;
    }
  | {
      entityType: 'host-provider-config-group';
      args: SaveHostProviderGroupConfigurationArgs;
    }
  | {
      entityType: 'cluster';
      args: SaveClusterConfigurationArgs;
    }
  | {
      entityType: 'cluster-config-group';
      args: SaveClusterGroupConfigurationArgs;
    }
  | {
      entityType: 'host';
      args: SaveHostConfigurationArgs;
    }
  | {
      entityType: 'service';
      args: SaveClusterServiceConfigurationArgs;
    }
  | {
      entityType: 'service-config-group';
      args: SaveClusterServiceGroupConfigurationArgs;
    }
  | {
      entityType: 'service-component';
      args: SaveClusterServiceComponentConfigurationArgs;
    }
  | {
      entityType: 'service-component-config-group';
      args: SaveClusterServiceComponentGroupConfigurationArgs;
    };

export type ApiRequestsDictionary = {
  [key in EntityType]: {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) => Promise<Batch<AdcmConfigShortView>>;
    getConfig: (args: LoadConfigurationArgs) => Promise<AdcmConfig>;
    getConfigSchema: (args: LoadConfigurationArgs) => Promise<SchemaDefinition>;
    createConfig: (args: SaveConfigurationArgs) => Promise<AdcmConfig>;
  };
};
