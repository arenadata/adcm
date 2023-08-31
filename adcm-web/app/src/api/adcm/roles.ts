import { httpClient } from '@api/httpClient';
import { PaginationParams, SortParams } from '@models/table';
import qs from 'qs';
import { prepareQueryParams } from '@utils/apiUtils';
import { Batch, AdcmCreateRolePayload, AdcmRole, AdcmRolesFilter, AdcmUpdateRolePayload } from '@models/adcm';

const productsMock = {
  count: 3,
  results: [
    {
      id: 1,
      name: 'ADQM',
    },
    {
      id: 2,
      name: 'ADS',
    },
    {
      id: 3,
      name: 'ADH',
    },
  ],
};

export class AdcmRolesApi {
  public static async createRole(payload: AdcmCreateRolePayload) {
    await httpClient.post('/api/v2/rbac/roles/', payload);
  }

  public static async getRole(id: number) {
    const response = await httpClient.get<AdcmRole>(`/api/v2/rbac/roles/${id}/`);
    return response.data;
  }

  public static async deleteRole(id: number) {
    await httpClient.delete(`/api/v2/rbac/roles/${id}/`);
  }

  public static async getRoles(filter: AdcmRolesFilter, sortParams?: SortParams, paginationParams?: PaginationParams) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmRole>>(`/api/v2/rbac/roles/?${query}`);
    return response.data;
  }

  public static async getProducts() {
    // const response = await httpClient.get<Batch<[]>>(`/api/v2/rbac/roles/products/`);
    // return response.data;
    return productsMock;
  }

  public static async updateRole(id: number, payload: AdcmUpdateRolePayload) {
    await httpClient.patch(`/api/v2/rbac/roles/${id}/`, payload);
  }
}
