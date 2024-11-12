import { httpClient } from '@api/httpClient';
import type {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export interface GetHostProviderGroupConfigsArgs {
  hostProviderId: number;
  configGroupId: number;
}

export interface GetHostProviderGroupConfigArgs {
  hostProviderId: number;
  configGroupId: number;
  configId: number;
}

interface GetHostProviderGroupConfigSchemaArgs {
  hostProviderId: number;
  configGroupId: number;
}

export interface CreateHostProviderGroupConfigArgs {
  hostProviderId: number;
  configGroupId: number;
  description?: string;
  configurationData: ConfigurationData;
  attributes: ConfigurationAttributes;
}

export class AdcmHostProviderGroupConfigsConfigsApi {
  public static async getConfigs(args: GetHostProviderGroupConfigsArgs) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/hostproviders/${args.hostProviderId}/config-groups/${args.configGroupId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(args: GetHostProviderGroupConfigArgs) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/hostproviders/${args.hostProviderId}/config-groups/${args.configGroupId}/configs/${args.configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(args: GetHostProviderGroupConfigSchemaArgs) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/hostproviders/${args.hostProviderId}/config-groups/${args.configGroupId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(args: CreateHostProviderGroupConfigArgs) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/hostproviders/${args.hostProviderId}/config-groups/${args.configGroupId}/configs/`,
      {
        description: args.description ?? '',
        adcmMeta: args.attributes,
        config: args.configurationData,
      },
    );
    return response.data;
  }
}
