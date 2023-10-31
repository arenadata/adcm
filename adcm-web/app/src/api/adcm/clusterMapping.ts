import { httpClient } from '@api/httpClient';
import { AdcmMapping, AdcmHostShortView, AdcmMappingComponent } from '@models/adcm/';

export class AdcmClusterMappingApi {
  public static async getMapping(clusterId: number) {
    const response = await httpClient.get<AdcmMapping[]>(`/api/v2/clusters/${clusterId}/mapping/`);
    return response.data;
  }

  public static async postMapping(clusterId: number, mapping: AdcmMapping[]) {
    await httpClient.post(`/api/v2/clusters/${clusterId}/mapping/`, mapping);
  }

  public static async getMappingHosts(clusterId: number) {
    const response = await httpClient.get<AdcmHostShortView[]>(`/api/v2/clusters/${clusterId}/mapping/hosts/`);
    return response.data;
  }

  public static async getMappingComponents(clusterId: number) {
    const response = await httpClient.get<AdcmMappingComponent[]>(`/api/v2/clusters/${clusterId}/mapping/components/`);
    return response.data;
  }
}
