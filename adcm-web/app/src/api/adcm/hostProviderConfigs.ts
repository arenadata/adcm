import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export class AdcmHostProviderConfigsApi {
  public static async getConfigs(hostProviderId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/hostproviders/${hostProviderId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(hostProviderId: number, configId: number) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/hostproviders/${hostProviderId}/configs/${configId}/`);
    return response.data;
  }

  public static async getConfigSchema(hostProviderId: number) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/hostproviders/${hostProviderId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(
    hostProviderId: number,
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
    description = '',
  ) {
    const response = await httpClient.post<AdcmConfig>(`/api/v2/hostproviders/${hostProviderId}/configs/`, {
      description,
      adcmMeta: attributes,
      config: configurationData,
    });
    return response.data;
  }
}
