import type { AdcmService } from '@models/adcm';
import { httpClient } from '@api/httpClient';

export class AdcmServicesApi {
  public static async getService(clusterId: number, serviceId: number) {
    const response = await httpClient.get<AdcmService>(`/api/v2/clusters/${clusterId}/services/${serviceId}/`);
    return response.data;
  }

  public static async deleteService(clusterId: number, serviceId: number) {
    await httpClient.delete(`/api/v2/clusters/${clusterId}/services/${serviceId}/`);
  }
}
