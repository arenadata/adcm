import { httpClient } from '@api/httpClient';
import type {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetClusterGroupConfigsArgs {
  clusterId: number;
  configGroupId: number;
}

export interface GetClusterGroupConfigArgs {
  clusterId: number;
  configGroupId: number;
  configId: number;
}

interface GetClusterGroupConfigSchemaArgs {
  clusterId: number;
  configGroupId: number;
}

export interface CreateClusterGroupConfigArgs {
  clusterId: number;
  configGroupId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmClusterGroupConfigsConfigsApi {
  public static async getConfigs(args: GetClusterGroupConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${args.clusterId}/config-groups/${args.configGroupId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetClusterGroupConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/config-groups/${args.configGroupId}/configs/${args.configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetClusterGroupConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${args.clusterId}/config-groups/${args.configGroupId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateClusterGroupConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/config-groups/${args.configGroupId}/configs/`,
      {
        description: args.description ?? '',
        adcmMeta: args.attributes,
        config: args.configurationData,
      },
    );
    return response.data;
  }
}
