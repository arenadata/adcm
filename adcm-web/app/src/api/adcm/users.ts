import { httpClient } from '@api/httpClient';
import { PaginationParams, SortParams } from '@models/table';
import { Batch, AdcmUsersFilter, CreateAdcmUserPayload, UpdateAdcmUserPayload, AdcmUser } from '@models/adcm';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';

export class AdcmUsersApi {
  public static async getUsers(filter: AdcmUsersFilter, sortParams?: SortParams, paginationParams?: PaginationParams) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmUser>>(`/api/v2/rbac/users/?${query}`);
    return response.data;
  }

  public static async postUser(payload: CreateAdcmUserPayload) {
    const mockPayload = {
      name: payload.name,
      description: payload.description,
    };

    await httpClient.post('/api/v2/rbac/users/', mockPayload);
  }

  public static async getUser(id: number) {
    const response = await httpClient.get<AdcmUser>(`/api/v2/rbac/users/${id}/`);
    return response.data;
  }

  public static async patchUser(id: number, payload: UpdateAdcmUserPayload) {
    await httpClient.patch(`/api/v2/rbac/users/${id}/`, payload);
  }

  public static async deleteUser(id: number) {
    await httpClient.delete(`/api/v2/rbac/users/${id}/`);
  }

  public static async deleteUsers(ids: number[]) {
    const mockPayload = ids.map((id) => ({ id }));
    await httpClient.post('/api/v2/rbac/users/delete/', mockPayload);
  }
}
