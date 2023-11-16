import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export class AdcmHostConfigsApi {
  public static async getConfigs(hostId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/hosts/${hostId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(hostId: number, configId: number) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/hosts/${hostId}/configs/${configId}/`);
    return response.data;
  }

  public static async getConfigSchema(hostId: number) {
    const response = await httpClient.get<ConfigurationSchema>(`/api/v2/hosts/${hostId}/config-schema/`);
    return response.data;
  }

  public static async createConfiguration(
    hostId: number,
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
    description = '',
  ) {
    const response = await httpClient.post<AdcmConfig>(`/api/v2/hosts/${hostId}/configs/`, {
      description,
      adcmMeta: attributes,
      config: configurationData,
    });
    return response.data;
  }
}
