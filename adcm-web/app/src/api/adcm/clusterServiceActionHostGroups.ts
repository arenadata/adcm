import { httpClient } from '@api/httpClient';
import type { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmJob, Batch } from '@models/adcm';
import type {
  AdcmActionHostGroup,
  GetAdcmServiceActionHostGroupsArgs,
  GetAdcmServiceActionHostGroupArgs,
  CreateAdcmServiceActionHostGroupArgs,
  DeleteAdcmServiceActionHostGroupArgs,
  GetAdcmServiceActionHostGroupActionsArgs,
  GetAdcmServiceActionHostGroupActionArgs,
  RunAdcmServiceActionHostGroupActionArgs,
  GetAdcmServiceActionHostGroupsHostCandidatesArgs,
  AdcmActionHostGroupHost,
  GetAdcmServiceActionHostGroupHostCandidatesArgs,
  GetAdcmServiceActionHostGroupHostsArgs,
  AddAdcmServiceActionHostGroupHostArgs,
  DeleteAdcmServiceActionHostGroupHostArgs,
} from '@models/adcm/actionHostGroup';
import { prepareQueryParams } from '@utils/apiUtils';
import qs from 'qs';

export class AdcmClusterServiceActionHostGroupsApi {
  // CRUD

  public static async getActionHostGroups(args: GetAdcmServiceActionHostGroupsArgs) {
    const { clusterId, serviceId, filter, paginationParams } = args;
    const queryParams = prepareQueryParams(filter, undefined, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmActionHostGroup>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroup(args: GetAdcmServiceActionHostGroupArgs) {
    const { clusterId, serviceId, actionHostGroupId } = args;
    const response = await httpClient.get<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/`,
    );

    return response.data;
  }

  public static async postActionHostGroup(args: CreateAdcmServiceActionHostGroupArgs) {
    const { clusterId, serviceId, actionHostGroup } = args;
    const response = await httpClient.post<AdcmActionHostGroup>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/`,
      actionHostGroup,
    );

    return response.data;
  }

  public static async deleteActionHostGroup(args: DeleteAdcmServiceActionHostGroupArgs) {
    const { clusterId, serviceId, actionHostGroupId } = args;
    await httpClient.delete(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/`,
    );
  }

  // Actions

  public static async getActionHostGroupActions(args: GetAdcmServiceActionHostGroupActionsArgs) {
    const { clusterId, serviceId, actionHostGroupId, sortParams, filter, paginationParams } = args;
    const queryParams = prepareQueryParams(filter, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmDynamicAction[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroupAction(args: GetAdcmServiceActionHostGroupActionArgs) {
    const { clusterId, serviceId, actionHostGroupId, actionId } = args;
    const response = await httpClient.get<AdcmDynamicActionDetails>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/`,
    );

    return response.data;
  }

  public static async postActionHostGroupAction(args: RunAdcmServiceActionHostGroupActionArgs) {
    const { clusterId, serviceId, actionHostGroupId, actionId, actionRunConfig } = args;
    const response = await httpClient.post<AdcmJob>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/actions/${actionId}/run/`,
      actionRunConfig,
    );

    return response.data;
  }

  // Host candidates

  public static async getActionHostGroupsHostCandidates(args: GetAdcmServiceActionHostGroupsHostCandidatesArgs) {
    const { clusterId, serviceId, filter } = args;
    const queryParams = prepareQueryParams(filter);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmActionHostGroupHost[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/host-candidates/?${query}`,
    );

    return response.data;
  }

  public static async getActionHostGroupHostCandidates(args: GetAdcmServiceActionHostGroupHostCandidatesArgs) {
    const { clusterId, serviceId, actionHostGroupId, filter } = args;
    const queryParams = prepareQueryParams(filter);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<AdcmActionHostGroupHost[]>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/host-candidates/?${query}`,
    );

    return response.data;
  }

  // Hosts

  public static async getActionHostGroupHosts(args: GetAdcmServiceActionHostGroupHostsArgs) {
    const { clusterId, serviceId, actionHostGroupId, sortParams, paginationParams } = args;
    const queryParams = prepareQueryParams(undefined, sortParams, paginationParams);
    const query = qs.stringify(queryParams);

    const response = await httpClient.get<Batch<AdcmActionHostGroupHost>>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/hosts/?${query}`,
    );

    return response.data;
  }

  public static async postActionHostGroupHost(args: AddAdcmServiceActionHostGroupHostArgs) {
    const { clusterId, serviceId, actionHostGroupId, hostId } = args;
    const response = await httpClient.post<AdcmActionHostGroupHost>(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/hosts/`,
      { hostId },
    );

    return response.data;
  }

  public static async deleteActionHostGroupHost(args: DeleteAdcmServiceActionHostGroupHostArgs) {
    const { clusterId, serviceId, actionHostGroupId, hostId } = args;
    await httpClient.delete(
      `/api/v2/clusters/${clusterId}/services/${serviceId}/action-host-groups/${actionHostGroupId}/hosts/${hostId}/`,
    );
  }
}
