import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export class AdcmSettingsApi {
  public static async getSettings() {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>('/api/v2/adcm/');
    return response.data;
  }

  public static async getConfigs() {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>('/api/v2/adcm/configs/');
    return response.data;
  }

  public static async getConfig(configId: number) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/adcm/configs/${configId}/`);
    return response.data;
  }

  public static async getConfigSchema() {
    const response = await httpClient.get<ConfigurationSchema>('/api/v2/adcm/config-schema/');
    return response.data;
  }

  public static async createConfiguration(
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
    description = '',
  ) {
    const response = await httpClient.post<AdcmConfig>('/api/v2/adcm/configs/', {
      description,
      adcmMeta: attributes,
      config: configurationData,
    });
    return response.data;
  }
}
