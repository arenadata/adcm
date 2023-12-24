import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
  AdcmSettings,
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
} from '@models/adcm';

export class AdcmSettingsApi {
  public static async getSettings() {
    const response = await httpClient.get<AdcmSettings>('/api/v2/adcm/');
    return response.data;
  }

  public static async getConfigs() {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>('/api/v2/adcm/configs/?offset=0&limit=1000');
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

  public static async getAdcmSettingsActions() {
    const response = await httpClient.get<AdcmDynamicAction[]>('/api/v2/adcm/actions/');
    return response.data;
  }

  public static async getAdcmSettingsActionDetails(actionId: number) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(`/api/v2/adcm/actions/${actionId}/`);
    return response.data;
  }

  public static async runAdcmSettingsAction(actionId: number, actionRunConfig: AdcmDynamicActionRunConfig) {
    const response = await httpClient.post(`/api/v2/adcm/actions/${actionId}/run/`, actionRunConfig);

    return response.data;
  }
}
