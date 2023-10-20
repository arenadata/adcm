import { httpClient } from '@api/httpClient';
import { Batch, AdcmConfigGroup, AdcmHostCandidate } from '@models/adcm';
import { EmptyTableFilter, PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export type AdcmClusterConfigGroupCreateData = Omit<AdcmConfigGroup, 'id' | 'hosts'>;

export class AdcmClusterConfigGroupsApi {
  public static async getConfigGroups(
    clusterId: number,
    filter?: EmptyTableFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmConfigGroup>>(
      `/api/v2/clusters/${clusterId}/config-groups/?${query}`,
    );
    return response.data;
  }

  public static async createConfigGroup(clusterId: number, data: AdcmClusterConfigGroupCreateData) {
    const response = await httpClient.post<AdcmConfigGroup>(`/api/v2/clusters/${clusterId}/config-groups/`, data);
    return response.data;
  }

  public static async deleteConfigGroup(clusterId: number, configGroupId: number) {
    const response = await httpClient.delete(`/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/`);
    return response.data;
  }

  public static async getConfigGroupHostsCandidates(clusterId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmHostCandidate[]>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/host-candidates/`,
    );
    return response.data;
  }

  public static async getConfigGroupMappedHosts(clusterId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmHostCandidate[]>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/hosts/`,
    );
    return response.data;
  }

  /**
   * @deprecated
   */
  public static async saveConfigGroupMappedHosts(clusterId: number, configGroupId: number, mappedHostsIds: number[]) {
    const response = await httpClient.post<AdcmConfigGroup>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/hosts/`,
      mappedHostsIds,
    );
    return response.data;
  }

  public static async mappedHostToConfigGroup(clusterId: number, configGroupId: number, hostId: number) {
    await httpClient.post(`/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/hosts/`, {
      hostId,
    });
  }

  public static async unmappedHostToConfigGroup(clusterId: number, configGroupId: number, hostId: number) {
    await httpClient.delete<AdcmConfigGroup>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/hosts/${hostId}/`,
    );
  }

  public static async getConfigGroup(clusterId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmConfigGroup>(
      `/api/v2/clusters/${clusterId}/config-groups/${configGroupId}/`,
    );
    return response.data;
  }
}
