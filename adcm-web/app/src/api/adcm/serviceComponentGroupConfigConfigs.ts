import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetClusterServiceComponentGroupConfigsArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
}

export interface GetClusterServiceComponentGroupConfigArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
  configId: number;
}

interface GetClusterServiceComponentGroupConfigSchemaArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
}

export interface CreateClusterServiceComponentGroupConfigArgs {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmClusterServiceComponentGroupConfigConfigsApi {
  public static async getConfigs(args: GetClusterServiceComponentGroupConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/config-groups/${args.configGroupId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetClusterServiceComponentGroupConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/config-groups/${args.configGroupId}/configs/${args.configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetClusterServiceComponentGroupConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/config-groups/${args.configGroupId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateClusterServiceComponentGroupConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/components/${args.componentId}/config-groups/${args.configGroupId}/configs/`,
      {
        description: args.description ?? '',
        adcmMeta: args.attributes,
        config: args.configurationData,
      },
    );
    return response.data;
  }
}
