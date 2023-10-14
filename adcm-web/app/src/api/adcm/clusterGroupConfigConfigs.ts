import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export class AdcmClusterGroupConfigsConfigsApi {
  public static async getConfigs(clusterId: number, configGroupId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/configs/`,
    );
    return response.data;
  }

  public static async getConfig(clusterId: number, configGroupId: number, configId: number) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/configs/${configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(clusterId: number, configGroupId: number) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(
    clusterId: number,
    configGroupId: number,
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
    description = '',
  ) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/configs/`,
      {
        description,
        adcmMeta: attributes,
        config: configurationData,
      },
    );
    return response.data;
  }
}
