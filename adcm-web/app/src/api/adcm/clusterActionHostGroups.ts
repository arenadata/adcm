import { httpClient } from '@api/httpClient';
import type { PaginationParams, SortParams } from '@models/table';
import type {
  AdcmDynamicAction,
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
  AdcmJob,
  Batch,
} from '@models/adcm';
import type {
  AdcmActionHostGroupHost,
  AdcmActionHostGroup,
  AdcmActionHostGroupsActionsFilter,
  AddAdcmActionHostGroupHostPayload,
  CreateAdcmActionHostGroupPayload,
} from '@models/adcm/actionHostGroup';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmClusterActionHostGroupsApi {
  public static async getActionHostGroups(clusterId: number, paginationParams: PaginationParams) {
    const queryParams = prepareQueryParams(undefined, undefined, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmActionHostGroup>>(
      `/api/v2/clusters/${clusterId}/action-host-groups/?${query}`,
    );

    return response.data;
  }

  public static async postActionHostGroup(clusterId: number, newActionGroup: CreateAdcmActionHostGroupPayload) {
    const response = await httpClient.post<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/action-host-groups/`,
      newActionGroup,
    );

    return response.data;
  }

  public static async getActionHostGroup(clusterId: number, actionHostGroupId: number) {
    await httpClient.get<AdcmActionHostGroup>(`/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/`);
  }

  public static async deleteActionHostGroup(clusterId: number, actionHostGroupId: number) {
    const response = await httpClient.delete<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/`,
    );

    return response.data;
  }

  public static async getActionHostGroupActions(
    clusterId: number,
    actionHostGroupId: number,
    sortParams: SortParams,
    paginationParams: PaginationParams,
    filter: AdcmActionHostGroupsActionsFilter,
  ) {
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmDynamicAction>>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroupAction(clusterId: number, actionHostGroupId: number, actionId: number) {
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/`,
    );

    return response.data;
  }

  public static async postActionHostGroupAction(
    clusterId: number,
    actionHostGroupId: number,
    actionId: number,
    actionRunConfig: AdcmDynamicActionRunConfig,
  ) {
    const response = await httpClient.post<AdcmJob>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }

  public static async postActionHostGroupHost(
    clusterId: number,
    actionHostGroupId: number,
    host: AddAdcmActionHostGroupHostPayload,
  ) {
    const response = await httpClient.post<AdcmActionHostGroupHost>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/hosts/`,
      host,
    );

    return response.data;
  }

  public static async deleteActionHostGroupHost(clusterId: number, actionHostGroupId: number, hostId: number) {
    await httpClient.delete<AdcmActionHostGroupHost>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/hosts/${hostId}/`,
    );
  }

  public static async getActionHostGroupHostCandidates(clusterId: number, actionHostGroupId: number) {
    const response = await httpClient.get<AdcmActionHostGroupHost[]>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/host-candidates/`,
    );

    return response.data;
  }
}
