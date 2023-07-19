import { httpClient } from '@api/httpClient';
import qs from 'qs';
import {
  AdcmPrototype,
  AdcmPrototypesFilter,
  AdcmPrototypeVersions,
  AdcmPrototypeVersionsFilter,
  Batch,
} from '@models/adcm';
import { PaginationParams, SortParams } from '@models/table';

export class AdcmPrototypesApi {
  public static async getPrototypeVersions(filter: AdcmPrototypeVersionsFilter) {
    const queryParams = {
      type: filter.type || undefined,
    };

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<AdcmPrototypeVersions[]>(`/api/v2/prototypes/versions/?${query}`);
    return response.data;
  }

  public static async postAcceptLicense(prototypeId: number) {
    const response = await httpClient.post(`/api/v2/prototypes/${prototypeId}/license/accept/`);
    return response.data;
  }

  public static async getPrototypes(
    filter: AdcmPrototypesFilter,
    sortParams: SortParams,
    paginationParams: PaginationParams,
  ) {
    const queryParams = {
      type: filter.type || undefined,
      sortColumn: sortParams.sortBy,
      sortDirection: sortParams.sortDirection,
      offset: paginationParams.pageNumber * paginationParams.perPage,
      limit: paginationParams.perPage,
    };

    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmPrototype>>(`/api/v2/prototypes/?${query}`);
    return response.data;
  }
}
