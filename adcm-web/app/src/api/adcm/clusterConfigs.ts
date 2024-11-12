import { httpClient } from '@api/httpClient';
import type {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetClusterConfigsArgs {
  clusterId: number;
}

export interface GetClusterConfigArgs {
  clusterId: number;
  configId: number;
}

interface GetClusterConfigSchemaArgs {
  clusterId: number;
}

export interface CreateClusterConfigArgs {
  clusterId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmClusterConfigsApi {
  public static async getConfigs(args: GetClusterConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${args.clusterId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetClusterConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/clusters/${args.clusterId}/configs/${args.configId}/`);
    return response.data;
  }

  public static async getConfigSchema(args: GetClusterConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(`/api/v2/clusters/${args.clusterId}/config-schema/`);
    return response.data;
  }

  public static async createConfiguration(args: CreateClusterConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(`/api/v2/clusters/${args.clusterId}/configs/`, {
      description: args.description ?? '',
      adcmMeta: args.attributes,
      config: args.configurationData,
    });
    return response.data;
  }
}
