import qs from 'qs';
import type { Batch } from '@models/adcm';
import { httpClient } from '@api/httpClient';
import { AdcmHostProvider, AdcmHostProviderFilter } from '@models/adcm/hostProvider';
import { PaginationParams, SortParams } from '@models/table';
import { AdcmHostProviderPayload } from '@models/adcm';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmHostProvidersApi {
  public static async getHostProviders(
    filter: AdcmHostProviderFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmHostProvider>>(`/api/v2/hostproviders/?${query}`);
    return response.data;
  }

  public static async postHostProviders(payload: AdcmHostProviderPayload) {
    const mockPayload = {
      name: payload.name,
      prototype: payload.prototypeId,
      description: payload.description,
    };

    await httpClient.post('/api/v2/hostproviders/', mockPayload);
  }

  public static async deleteHostProvider(id: number) {
    await httpClient.delete(`/api/v2/hostproviders/${id}/`);
  }
}
