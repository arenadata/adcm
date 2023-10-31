import { httpClient } from '@api/httpClient';
import { AdcmObjectCandidates, Batch } from '@models/adcm';
import { AdcmPoliciesFilter, AdcmPolicyPayload, AdcmPolicy } from '@models/adcm/policy';
import { PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmPoliciesApi {
  public static async getPolicies(
    filter: AdcmPoliciesFilter,
    paginationParams: PaginationParams,
    sortParams: SortParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);

    const query = qs.stringify(queryParams);
    const response = await httpClient.get<Batch<AdcmPolicy>>(`/api/v2/rbac/policies/?${query}`);
    return response.data;
  }

  public static async getPolicy(policyId: number) {
    const response = await httpClient.get<AdcmPolicy>(`/api/v2/rbac/policies/${policyId}/`);
    return response.data;
  }

  public static async createPolicy(payload: AdcmPolicyPayload) {
    await httpClient.post('/api/v2/rbac/policies/', payload);
  }

  public static async updatePolicy(policyId: number, payload: AdcmPolicyPayload) {
    await httpClient.patch(`/api/v2/rbac/policies/${policyId}/`, payload);
  }

  public static async deletePolicy(policyId: number) {
    const response = await httpClient.delete(`/api/v2/rbac/policies/${policyId}/`);
    return response.data;
  }

  public static async loadObjectCandidates(roleId: number) {
    const response = await httpClient.get<AdcmObjectCandidates>(`/api/v2/rbac/roles/${roleId}/object-candidates/`);
    return response.data;
  }
}
