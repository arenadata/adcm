import { httpClient } from '@api/httpClient';
import type { AdcmClusterMetrics } from '@models/adcm';

export class AdcmClusterMetricsApi {
  public static async getClusterMetrics(clusterId: number) {
    const response = await httpClient.get<AdcmClusterMetrics>(`/api/v2/cluster-metrics/${clusterId}/`);
    return response.data;
  }
}
