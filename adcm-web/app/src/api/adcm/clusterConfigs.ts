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
  configId: number;
};

type GetConfigSchemaArgs = {
  clusterId: number;
};

export class AdcmClusterConfigsApi {
  public static async getConfigs(clusterId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${clusterId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/clusters/${args.clusterId}/configs/${args.configId}/`);
    return response.data;
  }

  public static async getConfigSchema(args: GetConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(`/api/v2/clusters/${args.clusterId}/config-schema/`);
    return response.data;
  }

  public static async createConfiguration(
    clusterId: number,
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
    description = '',
  ) {
    const response = await httpClient.post<AdcmConfig>(`/api/v2/clusters/${clusterId}/configs/`, {
      description,
      adcmMeta: attributes,
      config: configurationData,
    });
    return response.data;
  }
}
