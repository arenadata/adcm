import { httpClient } from '@api/httpClient';
import {
  Batch,
  AdcmConfigShortView,
  AdcmConfig,
  ConfigurationSchema,
  ConfigurationData,
  ConfigurationAttributes,
} from '@models/adcm';

export class AdcmClusterServiceComponentsConfigsApi {
  public static async getConfigs(clusterId: number, serviceId: number, componentId: number) {
    const response = await httpClient.get<Batch<AdcmConfigShortView>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/configs/?offset=0&limit=1000`,
    );
    return response.data;
  }

  public static async getConfig(clusterId: number, serviceId: number, componentId: number, configId: number) {
    const response = await httpClient.get<AdcmConfig>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/configs/${configId}/`,
    );
    return response.data;
  }

  public static async getConfigSchema(clusterId: number, serviceId: number, componentId: number) {
    const response = await httpClient.get<ConfigurationSchema>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/config-schema/`,
    );
    return response.data;
  }

  public static async createConfiguration(
    clusterId: number,
    serviceId: number,
    componentId: number,
    configurationData: ConfigurationData,
    attributes: ConfigurationAttributes,
    description = '',
  ) {
    const response = await httpClient.post<AdcmConfig>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/components/${componentId}/configs/`,
      {
        description,
        adcmMeta: attributes,
        config: configurationData,
      },
    );
    return response.data;
  }
}
