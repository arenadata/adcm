import { httpClient } from '@api/httpClient';
import type {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetHostProviderConfigsArgs {
  hostProviderId: number;
}

export interface GetHostProviderConfigArgs {
  hostProviderId: number;
  configId: number;
}

interface GetHostProviderConfigSchemaArgs {
  hostProviderId: number;
}

export interface CreateHostProviderConfigArgs {
  hostProviderId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmHostProviderConfigsApi {
  public static async getConfigs(args: GetHostProviderConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/hostproviders/${args.hostProviderId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetHostProviderConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/hostproviders/${args.hostProviderId}/configs/${args.configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetHostProviderConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/hostproviders/${args.hostProviderId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateHostProviderConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(`/api/v2/hostproviders/${args.hostProviderId}/configs/`, {
      description: args.description ?? '',
      adcmMeta: args.attributes,
      config: args.configurationData,
    });
    return response.data;
  }
}
