import { httpClient } from '@api/httpClient';
import type {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetClusterServiceComponentConfigsArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

export interface GetClusterServiceComponentConfigArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configId: number;
}

interface GetClusterServiceComponentConfigSchemaArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

export interface CreateClusterServiceComponentConfigArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmClusterServiceComponentsConfigsApi {
  public static async getConfigs(args: GetClusterServiceComponentConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetClusterServiceComponentConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/configs/${args.configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetClusterServiceComponentConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateClusterServiceComponentConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/configs/`,
      {
        description: args.description ?? '',
        adcmMeta: args.attributes,
        config: args.configurationData,
      },
    );
    return response.data;
  }
}
