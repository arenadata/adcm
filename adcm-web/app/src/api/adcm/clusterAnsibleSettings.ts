import { httpClient } from '@api/httpClient';
import type { AdcmConfig, ConfigurationSchema } from '@models/adcm';

export interface GetClusterAnsibleSettingsArgs {
  clusterId: number;
}

export interface GetClusterAnsibleSettingsSchemaArgs {
  clusterId: number;
  configGroupId: number;
}

export interface CreateClusterAnsibleSettingsArgs {
  clusterId: number;
  config: Partial<AdcmConfig>;
}

export class AdcmClusterAnsibleSettingsApi {
  public static async getConfig(args: GetClusterAnsibleSettingsArgs) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/clusters/${args.clusterId}/ansible-config/`);
    return response.data;
  }

  public static async getConfigSchema(args: GetClusterAnsibleSettingsSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${args.clusterId}/ansible-config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateClusterAnsibleSettingsArgs) {
    const { clusterId, config } = args;
    const response = await httpClient.post<AdcmConfig>(`/api/v2/clusters/${clusterId}/ansible-config/`, config);
    return response.data;
  }
}
