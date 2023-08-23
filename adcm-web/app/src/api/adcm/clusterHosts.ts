import { httpClient } from '@api/httpClient';
import { AdcmClusterHost, AdcmClusterHostsFilter, AddClusterHostsPayload } from '@models/adcm/clusterHosts';
import { Batch } from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils.ts';
import qs from 'qs';

export class AdcmClusterHostsApi {
  public static async getClusterHosts(
    clusterId: number,
    filter: AdcmClusterHostsFilter,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmClusterHost>>(`/api/v2/clusters/${clusterId}/hosts/?${query}`);
    return response.data;
  }

  public static async addClusterHosts(payload: AddClusterHostsPayload) {
    const hostIds = payload.hostIds.map((id) => ({ hostId: id }));
    const response = await httpClient.post<AddClusterHostsPayload>(
      `/api/v2/clusters/${payload.clusterId}/hosts/`,
      hostIds,
    );
    return response.data;
  }
}
