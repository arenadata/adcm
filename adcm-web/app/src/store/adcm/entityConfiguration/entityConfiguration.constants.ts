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
  AdcmClusterAnsibleSettingsApi,
} from '@api';
import {
  ApiRequestsDictionary,
  LoadConfigurationArgs,
  LoadConfigurationVersionsArgs,
  SaveConfigurationArgs,
  // Settings
  LoadSettingsConfigurationArgs,
  SaveSettingsConfigurationArgs,
  // Host provider
  LoadHostProviderConfigurationVersionsArgs,
  LoadHostProviderConfigurationArgs,
  SaveHostProviderConfigurationArgs,
  // Host provider group
  LoadHostProviderGroupConfigurationVersionsArgs,
  LoadHostProviderGroupConfigurationArgs,
  SaveHostProviderGroupConfigurationArgs,
  // Cluster
  LoadClusterConfigurationVersionsArgs,
  LoadClusterConfigurationArgs,
  SaveClusterConfigurationArgs,
  // Cluster group
  LoadClusterGroupConfigurationVersionsArgs,
  LoadClusterGroupConfigurationArgs,
  SaveClusterGroupConfigurationArgs,
  // Cluster ansible settings
  LoadClusterAnsibleSettingsArgs,
  LoadClusterAnsibleSettingsSchemaArgs,
  SaveClusterAnsibleSettingsArgs,
  // Host
  LoadHostConfigurationVersionsArgs,
  LoadHostConfigurationArgs,
  SaveHostConfigurationArgs,
  // Cluster service
  LoadClusterServiceConfigurationVersionsArgs,
  LoadClusterServiceConfigurationArgs,
  SaveClusterServiceConfigurationArgs,
  // Cluster service group
  LoadClusterServiceGroupConfigurationVersionsArgs,
  LoadClusterServiceGroupConfigurationArgs,
  SaveClusterServiceGroupConfigurationArgs,
  // Cluster service component
  LoadClusterServiceComponentConfigurationVersionsArgs,
  LoadClusterServiceComponentConfigurationArgs,
  SaveClusterServiceComponentConfigurationArgs,
  // Cluster service component group
  LoadClusterServiceComponentGroupConfigurationVersionsArgs,
  LoadClusterServiceComponentGroupConfigurationArgs,
  SaveClusterServiceComponentGroupConfigurationArgs,
} from './entityConfiguration.types';

export const ApiRequests: ApiRequestsDictionary = {
  settings: {
    getConfigVersions: () => AdcmSettingsApi.getConfigs(),
    getConfig: (args: LoadConfigurationArgs) => AdcmSettingsApi.getConfig(args as LoadSettingsConfigurationArgs),
    getConfigSchema: () => AdcmSettingsApi.getConfigSchema(),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmSettingsApi.createConfiguration(args as SaveSettingsConfigurationArgs),
  },
  'host-provider': {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmHostProviderConfigsApi.getConfigs(args as LoadHostProviderConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmHostProviderConfigsApi.getConfig(args as LoadHostProviderConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmHostProviderConfigsApi.getConfigSchema(args as LoadHostProviderConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmHostProviderConfigsApi.createConfiguration(args as SaveHostProviderConfigurationArgs),
  },
  'host-provider-config-group': {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmHostProviderGroupConfigsConfigsApi.getConfigs(args as LoadHostProviderGroupConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmHostProviderGroupConfigsConfigsApi.getConfig(args as LoadHostProviderGroupConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmHostProviderGroupConfigsConfigsApi.getConfigSchema(args as LoadHostProviderGroupConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmHostProviderGroupConfigsConfigsApi.createConfiguration(args as SaveHostProviderGroupConfigurationArgs),
  },
  cluster: {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmClusterConfigsApi.getConfigs(args as LoadClusterConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) => AdcmClusterConfigsApi.getConfig(args as LoadClusterConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterConfigsApi.getConfigSchema(args as LoadClusterConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmClusterConfigsApi.createConfiguration(args as SaveClusterConfigurationArgs),
  },
  'cluster-config-group': {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmClusterGroupConfigsConfigsApi.getConfigs(args as LoadClusterGroupConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterGroupConfigsConfigsApi.getConfig(args as LoadClusterGroupConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterGroupConfigsConfigsApi.getConfigSchema(args as LoadClusterGroupConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmClusterGroupConfigsConfigsApi.createConfiguration(args as SaveClusterGroupConfigurationArgs),
  },
  'cluster-ansible-settings': {
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterAnsibleSettingsApi.getConfig(args as LoadClusterAnsibleSettingsArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterAnsibleSettingsApi.getConfigSchema(args as LoadClusterAnsibleSettingsSchemaArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmClusterAnsibleSettingsApi.createConfiguration(args as SaveClusterAnsibleSettingsArgs),
  },
  host: {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmHostConfigsApi.getConfigs(args as LoadHostConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) => AdcmHostConfigsApi.getConfig(args as LoadHostConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmHostConfigsApi.getConfigSchema(args as LoadHostConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmHostConfigsApi.createConfiguration(args as SaveHostConfigurationArgs),
  },
  service: {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmClusterServicesConfigsApi.getConfigs(args as LoadClusterServiceConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServicesConfigsApi.getConfig(args as LoadClusterServiceConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServicesConfigsApi.getConfigSchema(args as LoadClusterServiceConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmClusterServicesConfigsApi.createConfiguration(args as SaveClusterServiceConfigurationArgs),
  },
  'service-config-group': {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmClusterServiceConfigGroupConfigsApi.getConfigs(args as LoadClusterServiceGroupConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceConfigGroupConfigsApi.getConfig(args as LoadClusterServiceGroupConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceConfigGroupConfigsApi.getConfigSchema(args as LoadClusterServiceGroupConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmClusterServiceConfigGroupConfigsApi.createConfiguration(args as SaveClusterServiceGroupConfigurationArgs),
  },
  'service-component': {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmClusterServiceComponentsConfigsApi.getConfigs(args as LoadClusterServiceComponentConfigurationVersionsArgs),
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentsConfigsApi.getConfig(args as LoadClusterServiceComponentConfigurationArgs),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentsConfigsApi.getConfigSchema(args as LoadClusterServiceComponentConfigurationArgs),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmClusterServiceComponentsConfigsApi.createConfiguration(args as SaveClusterServiceComponentConfigurationArgs),
  },
  'service-component-config-group': {
    getConfigVersions: (args: LoadConfigurationVersionsArgs) =>
      AdcmClusterServiceComponentGroupConfigConfigsApi.getConfigs(
        args as LoadClusterServiceComponentGroupConfigurationVersionsArgs,
      ),
    getConfig: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentGroupConfigConfigsApi.getConfig(
        args as LoadClusterServiceComponentGroupConfigurationArgs,
      ),
    getConfigSchema: (args: LoadConfigurationArgs) =>
      AdcmClusterServiceComponentGroupConfigConfigsApi.getConfigSchema(
        args as LoadClusterServiceComponentGroupConfigurationArgs,
      ),
    createConfig: (args: SaveConfigurationArgs) =>
      AdcmClusterServiceComponentGroupConfigConfigsApi.createConfiguration(
        args as SaveClusterServiceComponentGroupConfigurationArgs,
      ),
  },
};
