import { httpClient } from '@api/httpClient';
import type {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetClusterServiceGroupConfigsArgs {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
}
export interface GetClusterServiceGroupConfigArgs {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
  configId: number;
}

interface GetClusterServiceGroupConfigSchemaArgs {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
}

export interface CreateClusterServiceGroupConfigArgs {
  clusterId: number;
  serviceId: number;
  description?: string;
  configGroupId: number;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmClusterServiceConfigGroupConfigsApi {
  public static async getConfigs(args: GetClusterServiceGroupConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/config-groups/${args.configGroupId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetClusterServiceGroupConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/config-groups/${args.configGroupId}/configs/${args.configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetClusterServiceGroupConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/config-groups/${args.configGroupId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateClusterServiceGroupConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/config-groups/${args.configGroupId}/configs/`,
      {
        description: args.description ?? '',
        adcmMeta: args.attributes,
        config: args.configurationData,
      },
    );
    return response.data;
  }
}
