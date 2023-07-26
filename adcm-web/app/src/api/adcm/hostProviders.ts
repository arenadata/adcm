import qs from 'qs';
import type { Batch } from '@models/adcm';
import { httpClient } from '@api/httpClient';
import { AdcmHostProvider, AdcmHostProviderFilter } from '@models/adcm/hostProvider';
import { PaginationParams, SortParams } from '@models/table';

export class AdcmHostProvidersApi {
  public static async getHostProviders(
    filter: AdcmHostProviderFilter,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = {
      hostproviderName: filter.hostproviderName || undefined,
      prototype: filter.prototype || undefined,
      offset: paginationParams.pageNumber * paginationParams.perPage,
      limit: paginationParams.perPage,
      ordering: sortParams.sortBy,
    };

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmHostProvider>>(`/api/v2/hostproviders/?${query}`);
    return response.data;
  }

  public static async deleteHostProvider(id: number) {
    await httpClient.delete(`/api/v2/hostproviders/${id}/`);
  }
}
