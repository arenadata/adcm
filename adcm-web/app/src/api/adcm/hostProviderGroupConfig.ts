import { httpClient } from '@api/httpClient';
import type { Batch, AdcmConfigGroup, AdcmHostCandidate } from '@models/adcm';
import type { EmptyTableFilter, PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export type AdcmHostProviderConfigGroupCreateData = Omit<AdcmConfigGroup, 'id' | 'hosts'>;

export class AdcmHostProviderConfigGroupsApi {
  public static async getConfigGroups(
    hostProviderId: number,
    filter?: EmptyTableFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmConfigGroup>>(
      `/api/v2/hostproviders/${hostProviderId}/config-groups/?${query}`,
    );
    return response.data;
  }

  public static async createConfigGroup(hostProviderId: number, data: AdcmHostProviderConfigGroupCreateData) {
    const response = await httpClient.post<AdcmConfigGroup>(
      `/api/v2/hostproviders/${hostProviderId}/config-groups/`,
      data,
    );
    return response.data;
  }

  public static async deleteConfigGroup(hostProviderId: number, configGroupId: number) {
    const response = await httpClient.delete(`/api/v2/hostproviders/${hostProviderId}/config-groups/${configGroupId}/`);
    return response.data;
  }

  public static async getConfigGroupHostsCandidates(hostProviderId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmHostCandidate[]>(
      `/api/v2/hostproviders/${hostProviderId}/config-groups/${configGroupId}/host-candidates/`,
    );
    return response.data;
  }

  public static async getConfigGroupMappedHosts(hostProviderId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmHostCandidate[]>(
      `/api/v2/hostproviders/${hostProviderId}/config-groups/${configGroupId}/hosts/`,
    );
    return response.data;
  }

  /**
   * @deprecated
   */
  public static async saveConfigGroupMappedHosts(
    hostProviderId: number,
    configGroupId: number,
    mappedHostsIds: number[],
  ) {
    const response = await httpClient.post<AdcmConfigGroup>(
      `/api/v2/hostproviders/${hostProviderId}/config-groups/${configGroupId}/hosts/`,
      mappedHostsIds,
    );
    return response.data;
  }

  public static async mappedHostToConfigGroup(hostProviderId: number, configGroupId: number, hostId: number) {
    await httpClient.post(`/api/v2/hostproviders/${hostProviderId}/config-groups/${configGroupId}/hosts/`, {
      hostId,
    });
  }

  public static async unmappedHostToConfigGroup(hostProviderId: number, configGroupId: number, hostId: number) {
    await httpClient.delete<AdcmConfigGroup>(
      `/api/v2/hostproviders/${hostProviderId}/config-groups/${configGroupId}/hosts/${hostId}/`,
    );
  }

  public static async getConfigGroup(hostProviderId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmConfigGroup>(
      `/api/v2/hostproviders/${hostProviderId}/config-groups/${configGroupId}/`,
    );
    return response.data;
  }
}
