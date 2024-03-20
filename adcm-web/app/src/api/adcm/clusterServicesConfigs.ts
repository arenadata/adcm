import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetClusterServiceConfigsArgs {
  clusterId: number;
  serviceId: number;
}

export interface GetClusterServiceConfigArgs {
  clusterId: number;
  serviceId: number;
  configId: number;
}

interface GetClusterServiceConfigSchemaArgs {
  clusterId: number;
  serviceId: number;
}

export interface CreateClusterServiceConfigArgs {
  clusterId: number;
  serviceId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmClusterServicesConfigsApi {
  public static async getConfigs(args: GetClusterServiceConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetClusterServiceConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/configs/${args.configId}`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetClusterServiceConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateClusterServiceConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/configs/`,
      {
        description: args.description ?? '',
        adcmMeta: args.attributes,
        config: args.configurationData,
      },
    );
    return response.data;
  }
}
