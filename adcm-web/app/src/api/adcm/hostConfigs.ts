import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetHostConfigsArgs {
  hostId: number;
}

export interface GetHostConfigArgs {
  hostId: number;
  configId: number;
}

interface GetHostConfigSchemaArgs {
  hostId: number;
}

export interface CreateHostConfigArgs {
  hostId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmHostConfigsApi {
  public static async getConfigs(args: GetHostConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/hosts/${args.hostId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetHostConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(`/api/v2/hosts/${args.hostId}/configs/${args.configId}/`);
    return response.data;
  }

  public static async getConfigSchema(args: GetHostConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(`/api/v2/hosts/${args.hostId}/config-schema/`);
    return response.data;
  }

  public static async createConfiguration(args: CreateHostConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(`/api/v2/hosts/${args.hostId}/configs/`, {
      description: args.description ?? '',
      adcmMeta: args.attributes,
      config: args.configurationData,
    });
    return response.data;
  }
}
