import { httpClient } from '@api/httpClient';
import { PaginationParams } from '@models/table';
import {
  Batch,
  AdcmClustersFilter,
  AdcmCluster,
  CreateAdcmClusterPayload,
  UpdateAdcmClusterPayload,
} from '@models/adcm';
import qs from 'qs';

export class AdcmClustersApi {
  public static async getClusters(filter: AdcmClustersFilter, paginationParams: PaginationParams) {
    const queryParams = {
      name: filter.clusterName || undefined,
      status: filter.clusterStatus || undefined,
      prototype_name: filter.prototypeName || undefined,
      offset: paginationParams.pageNumber * paginationParams.perPage,
      limit: paginationParams.perPage,
    };

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmCluster>>(`/api/v2/clusters/?${query}`);
    return response.data;
  }

  public static async postCluster(payload: CreateAdcmClusterPayload) {
    const mockPayload = {
      name: payload.name,
      description: payload.description,
      prototype: payload.prototypeId,
    };

    await httpClient.post('/api/v2/clusters/', mockPayload);
  }

  public static async getCluster(clusterId: number) {
    const response = await httpClient.get<AdcmCluster>(`/api/v2/clusters/${clusterId}`);
    return response.data;
  }

  public static async patchCluster(clusterId: number, payload: UpdateAdcmClusterPayload) {
    await httpClient.patch(`/api/v2/clusters/${clusterId}`, payload);
  }

  public static async deleteCluster(clusterId: number) {
    await httpClient.delete(`/api/v2/clusters/${clusterId}`);
  }
}
