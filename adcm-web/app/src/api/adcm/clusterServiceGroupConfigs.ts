import { httpClient } from '@api/httpClient';
import { Batch, AdcmConfigGroup, AdcmHostCandidate } from '@models/adcm';
import { EmptyTableFilter, PaginationParams, SortParams } from '@models/table';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export type AdcmClusterServiceConfigGroupCreateData = Omit<AdcmConfigGroup, 'id' | 'hosts'>;

export class AdcmClusterServiceConfigGroupsApi {
  public static async getConfigGroups(
    clusterId: number,
    serviceId: number,
    filter?: EmptyTableFilter,
    sortParams?: SortParams,
    paginationParams?: PaginationParams,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmConfigGroup>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/?${query}`,
    );
    return response.data;
  }

  public static async createConfigGroup(
    clusterId: number,
    serviceId: number,
    data: AdcmClusterServiceConfigGroupCreateData,
  ) {
    const response = await httpClient.post<AdcmConfigGroup>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/`,
      data,
    );
    return response.data;
  }

  public static async deleteConfigGroup(clusterId: number, serviceId: number, configGroupId: number) {
    const response = await httpClient.delete(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/${configGroupId}/`,
    );
    return response.data;
  }

  public static async getConfigGroupHostsCandidates(clusterId: number, serviceId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmHostCandidate[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/${configGroupId}/host-candidates/`,
    );
    return response.data;
  }

  public static async getConfigGroupMappedHosts(clusterId: number, serviceId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmHostCandidate[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/${configGroupId}/hosts/`,
    );
    return response.data;
  }

  public static async saveConfigGroupMappedHosts(
    clusterId: number,
    serviceId: number,
    configGroupId: number,
    mappedHostsIds: number[],
  ) {
    const response = await httpClient.post<AdcmConfigGroup>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/${configGroupId}/hosts/`,
      mappedHostsIds,
    );
    return response.data;
  }

  public static async getConfigGroup(clusterId: number, serviceId: number, configGroupId: number) {
    const response = await httpClient.get<AdcmConfigGroup>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/config-groups/${configGroupId}/`,
    );
    return response.data;
  }
}
