import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export class AdcmClusterConfigsApi {
  public static async getConfigs(clusterId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(`/api/v2/clusters/${clusterId}/configs/`);
    return response.data;
  }

  public static async getConfig(clusterId: number, configId: number) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/clusters/${clusterId}/configs/${configId}/`);
    return response.data;
  }

  public static async getConfigSchema(clusterId: number, configId: number) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${clusterId}/configs/${configId}/schema/`,
    );
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
