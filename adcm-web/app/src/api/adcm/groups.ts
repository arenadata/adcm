import { httpClient } from '@api/httpClient';
import type { PaginationParams, SortParams } from '@models/table';
import type { Batch, AdcmGroup, AdcmCreateGroupPayload, AdcmUpdateGroupPayload, AdcmGroupFilter } from '@models/adcm';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmGroupsApi {
  public static async getGroups(
    filter?: AdcmGroupFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmGroup>>(`/api/v2/rbac/groups/?${query}`);
    return response.data;
  }

  public static async createGroup(payload: AdcmCreateGroupPayload) {
    await httpClient.post('/api/v2/rbac/groups/', payload);
  }

  public static async getGroup(id: number) {
    const response = await httpClient.get<AdcmGroup>(`/api/v2/rbac/groups/${id}/`);
    return response.data;
  }

  public static async updateGroup(id: number, payload: AdcmUpdateGroupPayload) {
    await httpClient.patch(`/api/v2/rbac/groups/${id}/`, payload);
  }

  public static async deleteGroup(id: number) {
    await httpClient.delete(`/api/v2/rbac/groups/${id}/`);
  }
}
