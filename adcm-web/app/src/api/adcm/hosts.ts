import qs from 'qs';
import type { Batch, CreateAdcmHostPayload } from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';
import { httpClient } from '@api/httpClient';
import { AdcmHost, AdcmHostsFilter } from '@models/adcm/host';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmHostsApi {
  public static async getHosts(filter: AdcmHostsFilter, sortParams: SortParams, paginationParams: PaginationParams) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmHost>>(`/api/v2/hosts/?${query}`);
    return response.data;
  }

  public static async deleteHost(id: number) {
    await httpClient.delete(`/api/v2/hosts/${id}/`);
  }

  public static async createHost(payload: CreateAdcmHostPayload) {
    await httpClient.post('/api/v2/hosts/', payload);
  }
}
