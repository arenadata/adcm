import qs from 'qs';
import type { Batch } from '@models/adcm';
import type { PaginationParams, SortParams } from '@models/table';
import { httpClient } from '@api/httpClient';
import type { AdcmBundle, AdcmBundlesFilter } from '@models/adcm/bundle';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmBundlesApi {
  public static async getBundles(
    filter: AdcmBundlesFilter,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmBundle>>(`/api/v2/bundles/?${query}`);
    return response.data;
  }

  public static async getBundle(id: number) {
    const response = await httpClient.get<AdcmBundle>(`/api/v2/bundles/${id}/`);
    return response.data;
  }

  public static async deleteBundle(id: number) {
    const response = await httpClient.delete(`/api/v2/bundles/${id}/`);
    return response.data;
  }

  public static async uploadBundle(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await httpClient.post('/api/v2/bundles/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
}
