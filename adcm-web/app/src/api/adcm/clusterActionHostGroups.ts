import { httpClient } from '@api/httpClient';
import type { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmSubJob, Batch } from '@models/adcm';
import type {
  AdcmActionHostGroup,
  GetAdcmClusterActionHostGroupsArgs,
  GetAdcmClusterActionHostGroupArgs,
  CreateAdcmClusterActionHostGroupArgs,
  DeleteAdcmClusterActionHostGroupArgs,
  GetAdcmClusterActionHostGroupActionsArgs,
  GetAdcmClusterActionHostGroupActionArgs,
  RunAdcmClusterActionHostGroupActionArgs,
  AdcmActionHostGroupHost,
  GetAdcmClusterActionHostGroupsHostCandidatesArgs,
  GetAdcmClusterActionHostGroupHostCandidatesArgs,
  GetAdcmClusterActionHostGroupHostsArgs,
  AddAdcmClusterActionHostGroupHostArgs,
  DeleteAdcmClusterActionHostGroupHostArgs,
} from '@models/adcm/actionHostGroup';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmClusterActionHostGroupsApi {
  // CRUD

  public static async getActionHostGroups(args: GetAdcmClusterActionHostGroupsArgs) {
    const { clusterId, filter, paginationParams } = args;
    const queryParams = prepareQueryParams(filter, undefined, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmActionHostGroup>>(
      `/api/v2/clusters/${clusterId}/action-host-groups/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroup(args: GetAdcmClusterActionHostGroupArgs) {
    const { clusterId, actionHostGroupId } = args;
    const response = await httpClient.get<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/`,
    );

    return response.data;
  }

  public static async postActionHostGroup(args: CreateAdcmClusterActionHostGroupArgs) {
    const { clusterId, actionHostGroup } = args;
    const response = await httpClient.post<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/action-host-groups/`,
      actionHostGroup,
    );

    return response.data;
  }

  public static async deleteActionHostGroup(args: DeleteAdcmClusterActionHostGroupArgs) {
    const { clusterId, actionHostGroupId } = args;
    await httpClient.delete(`/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/`);
  }

  // Actions

  public static async getActionHostGroupActions(args: GetAdcmClusterActionHostGroupActionsArgs) {
    const { clusterId, actionHostGroupId, sortParams, filter, paginationParams } = args;
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroupAction(args: GetAdcmClusterActionHostGroupActionArgs) {
    const { clusterId, actionHostGroupId, actionId } = args;
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/`,
    );

    return response.data;
  }

  public static async postActionHostGroupAction(args: RunAdcmClusterActionHostGroupActionArgs) {
    const { clusterId, actionHostGroupId, actionId, actionRunConfig } = args;
    const response = await httpClient.post<AdcmSubJob>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }

  // Host candidates

  public static async getActionHostGroupsHostCandidates(args: GetAdcmClusterActionHostGroupsHostCandidatesArgs) {
    const { clusterId, filter } = args;
    const queryParams = prepareQueryParams(filter);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmActionHostGroupHost[]>(
      `/api/v2/clusters/${clusterId}/action-host-groups/host-candidates/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroupHostCandidates(args: GetAdcmClusterActionHostGroupHostCandidatesArgs) {
    const { clusterId, actionHostGroupId, filter } = args;
    const queryParams = prepareQueryParams(filter);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmActionHostGroupHost[]>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/host-candidates/?${query}`,
    );

    return response.data;
  }

  // Hosts

  public static async getActionHostGroupHosts(args: GetAdcmClusterActionHostGroupHostsArgs) {
    const { clusterId, actionHostGroupId, sortParams, paginationParams } = args;
    const queryParams = prepareQueryParams(undefined, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmActionHostGroupHost>>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/hosts/?${query}`,
    );

    return response.data;
  }

  public static async postActionHostGroupHost(args: AddAdcmClusterActionHostGroupHostArgs) {
    const { clusterId, actionHostGroupId, hostId } = args;
    const response = await httpClient.post<AdcmActionHostGroupHost>(
      `/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/hosts/`,
      { hostId },
    );

    return response.data;
  }

  public static async deleteActionHostGroupHost(args: DeleteAdcmClusterActionHostGroupHostArgs) {
    const { clusterId, actionHostGroupId, hostId } = args;
    await httpClient.delete(`/api/v2/clusters/${clusterId}/action-host-groups/${actionHostGroupId}/hosts/${hostId}/`);
  }
}
