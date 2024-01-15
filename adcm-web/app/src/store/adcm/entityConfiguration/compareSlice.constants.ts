import {
  AdcmSettingsApi,
  AdcmHostProviderConfigsApi,
  AdcmHostProviderGroupConfigsConfigsApi,
  AdcmClusterConfigsApi,
  AdcmClusterGroupConfigsConfigsApi,
  AdcmHostConfigsApi,
  AdcmClusterServicesConfigsApi,
  AdcmClusterServiceConfigGroupConfigsApi,
  AdcmClusterServiceComponentsConfigsApi,
  AdcmClusterServiceComponentGroupConfigConfigsApi,
} from '@api';
import {
  ApiRequestsDictionary,
  LoadConfigurationArgs,
  LoadSettingsConfigurationArgs,
  LoadHostProviderConfigurationArgs,
  LoadHostProviderGroupConfigurationArgs,
  LoadClusterConfigurationArgs,
  LoadClusterGroupConfigurationArgs,
  LoadHostConfigurationArgs,
  LoadServiceConfigurationArgs,
  LoadServiceGroupConfigurationArgs,
  LoadServiceComponentConfigurationArgs,
  LoadServiceComponentGroupConfigurationArgs,
} from './compareSlice.types';

export const ApiRequests: ApiRequestsDictionary = {
  settings: {
    getConfig: (args: LoadConfigurationArgs) => AdcmSettingsApi.getConfig(args as LoadSettingsConfigurationArgs),
    getConfigSchema: () => AdcmSettingsApi.getConfigSchema(),
  },
  'host-provider': {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmHostProviderConfigsApi.getConfig(args as LoadHostProviderConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmHostProviderConfigsApi.getConfigSchema(args as LoadHostProviderConfigurationArgs),
  },
  'host-provider-config-group': {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmHostProviderGroupConfigsConfigsApi.getConfig(args as LoadHostProviderGroupConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmHostProviderGroupConfigsConfigsApi.getConfigSchema(args as LoadHostProviderGroupConfigurationArgs),
  },
  cluster: {
    getConfig: (args: LoadConfigurationArgs) => AdcmClusterConfigsApi.getConfig(args as LoadClusterConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterConfigsApi.getConfigSchema(args as LoadClusterConfigurationArgs),
  },
  'cluster-config-group': {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterGroupConfigsConfigsApi.getConfig(args as LoadClusterGroupConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterGroupConfigsConfigsApi.getConfigSchema(args as LoadClusterGroupConfigurationArgs),
  },
  host: {
    getConfig: (args: LoadConfigurationArgs) => AdcmHostConfigsApi.getConfig(args as LoadHostConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmHostConfigsApi.getConfigSchema(args as LoadHostConfigurationArgs),
  },
  service: {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServicesConfigsApi.getConfig(args as LoadServiceConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServicesConfigsApi.getConfigSchema(args as LoadServiceConfigurationArgs),
  },
  'service-config-group': {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceConfigGroupConfigsApi.getConfig(args as LoadServiceGroupConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceConfigGroupConfigsApi.getConfigSchema(args as LoadServiceGroupConfigurationArgs),
  },
  'service-component': {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentsConfigsApi.getConfig(args as LoadServiceComponentConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentsConfigsApi.getConfigSchema(args as LoadServiceComponentConfigurationArgs),
  },
  'service-component-config-group': {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentGroupConfigConfigsApi.getConfig(args as LoadServiceComponentGroupConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentGroupConfigConfigsApi.getConfigSchema(
        args as LoadServiceComponentGroupConfigurationArgs,
      ),
  },
};
