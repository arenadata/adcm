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
  hostId: number;
  configId: number;
};

type GetConfigSchemaArgs = {
  hostId: number;
};

export class AdcmHostConfigsApi {
  public static async getConfigs(hostId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/hosts/${hostId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/hosts/${args.hostId}/configs/${args.configId}/`);
    return response.data;
  }

  public static async getConfigSchema(args: GetConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(`/api/v2/hosts/${args.hostId}/config-schema/`);
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
