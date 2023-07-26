import qs from 'qs';
import type { Batch } from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';
import { httpClient } from '@api/httpClient';
import { AdcmHost, AdcmHostsFilter } from '@models/adcm/host';

export class AdcmHostsApi {
  public static async getHosts(filter: AdcmHostsFilter, sortParams: SortParams, paginationParams: PaginationParams) {
    const queryParams = {
      hostName: filter.hostName || undefined,
      hostProvider: filter.hostProvider || undefined,
      clusterName: filter.clusterName || undefined,
      offset: paginationParams.pageNumber * paginationParams.perPage,
      limit: paginationParams.perPage,
    };

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmHost>>(`/api/v2/hosts/?${query}`);
    return response.data;
  }

  public static async deleteHost(id: number) {
    await httpClient.delete(`/api/v2/hosts/${id}/`);
  }
}
