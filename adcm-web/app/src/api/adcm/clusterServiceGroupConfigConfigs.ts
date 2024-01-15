import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

type GetConfigArgs = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
  configId: number;
};

type GetConfigSchemaArgs = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
};

export class AdcmClusterServiceConfigGroupConfigsApi {
  public static async getConfigs(clusterId: number, serviceId: number, configGroupId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/${configGroupId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/config-groups/${args.configGroupId}/configs/${args.configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${args.clusterId}/services/${args.serviceId}/config-groups/${args.configGroupId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(
    clusterId: number,
    serviceId: number,
    configGroupId: number,
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
    description = '',
  ) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/${configGroupId}/configs/`,
      {
        description,
        adcmMeta: attributes,
        config: configurationData,
      },
    );
    return response.data;
  }
}
